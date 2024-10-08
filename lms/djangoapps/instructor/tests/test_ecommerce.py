"""
Unit tests for Ecommerce feature flag in new instructor dashboard.
"""


import datetime

import pytz
import six
from django.urls import reverse
from django.conf import settings
from six import text_type
import unittest

from course_modes.models import CourseMode
from course_modes.tests.factories import CourseModeFactory
from openedx.core.djangoapps.site_configuration.tests.mixins import SiteMixin
from shoppingcart.models import Coupon, CourseRegistrationCode
from student.roles import CourseFinanceAdminRole
from student.tests.factories import AdminFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


class TestECommerceDashboardViews(SiteMixin, SharedModuleStoreTestCase):
    """
    Check for E-commerce view on the new instructor dashboard
    """

    @classmethod
    def setUpClass(cls):
        super(TestECommerceDashboardViews, cls).setUpClass()
        cls.course = CourseFactory.create()

        # URL for instructor dash
        cls.url = reverse('instructor_dashboard', kwargs={'course_id': text_type(cls.course.id)})
        cls.ecommerce_link = '<button type="button" class="btn-link e-commerce" data-section="e-commerce">E-Commerce</button>'

    def setUp(self):
        super(TestECommerceDashboardViews, self).setUp()

        # Create instructor account
        self.instructor = AdminFactory.create()
        self.client.login(username=self.instructor.username, password="test")
        mode = CourseModeFactory(
            course_id=text_type(self.course.id), mode_slug='honor',
            mode_display_name='honor', min_price=10, currency='usd'
        )
        mode.save()
        CourseFinanceAdminRole(self.course.id).add_users(self.instructor)

    def test_pass_e_commerce_tab_in_instructor_dashboard(self):
        """
        Test Pass E-commerce Tab is in the Instructor Dashboard
        """
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        # Coupons should show up for White Label sites with priced honor modes.
        self.assertContains(response, 'Coupon Code List')

    @unittest.skipIf(settings.TAHOE_ALWAYS_SKIP_TEST, 'Fails for unknown reasons')
    def test_reports_section_under_e_commerce_tab(self):
        """
        Test reports section, under E-commerce Tab, is in the Instructor Dashboard
        """
        self.use_site(site=self.site_other)
        self.client.login(username=self.instructor.username, password="test")
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        self.assertContains(response, 'Create Enrollment Report')

    def test_reports_section_not_under_e_commerce_tab(self):
        """
        Test reports section, under E-commerce Tab, should not be available in the Instructor Dashboard with default
        value
        """
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        self.assertNotContains(response, 'Create Enrollment Report')

    def test_user_has_finance_admin_rights_in_e_commerce_tab(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)

        # Order/Invoice sales csv button text should render in e-commerce page
        self.assertContains(response, 'Total Credit Card Purchases')
        self.assertContains(response, 'Download All Credit Card Purchases')
        self.assertContains(response, 'Download All Invoices')

        # removing the course finance_admin role of login user
        CourseFinanceAdminRole(self.course.id).remove_users(self.instructor)

        # Order/Invoice sales csv button text should not be visible in e-commerce page if the user is not finance admin
        url = reverse('instructor_dashboard', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.post(url)
        self.assertNotContains(response, 'Download All Invoices')

    def test_user_view_course_price(self):
        """
        test to check if the user views the set price button and price in
        the instructor dashboard
        """
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)

        # Total amount html should render in e-commerce page, total amount will be 0
        course_honor_mode = CourseMode.mode_for_course(self.course.id, 'honor')

        price = course_honor_mode.min_price
        self.assertContains(response, 'Course price per seat: <span>$' + str(price) + '</span>')
        self.assertNotContains(response, '+ Set Price</a></span>')

        # removing the course finance_admin role of login user
        CourseFinanceAdminRole(self.course.id).remove_users(self.instructor)

        # total amount should not be visible in e-commerce page if the user is not finance admin
        url = reverse('instructor_dashboard', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.get(url)
        self.assertNotContains(response, '+ Set Price</a></span>')

    def test_update_course_price_check(self):
        price = 200
        # course B
        course2 = CourseFactory.create(org='EDX', display_name='test_course', number='100')
        mode = CourseModeFactory(
            course_id=text_type(course2.id), mode_slug='honor',
            mode_display_name='honor', min_price=30, currency='usd'
        )
        mode.save()
        # course A update
        CourseMode.objects.filter(course_id=self.course.id).update(min_price=price)

        set_course_price_url = reverse('set_course_mode_price', kwargs={'course_id': text_type(self.course.id)})
        data = {'course_price': price, 'currency': 'usd'}
        response = self.client.post(set_course_price_url, data)
        self.assertContains(response, 'CourseMode price updated successfully')

        # Course A updated total amount should be visible in e-commerce page if the user is finance admin
        url = reverse('instructor_dashboard', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.get(url)

        self.assertContains(response, 'Course price per seat: <span>$' + str(price) + '</span>')

    def test_user_admin_set_course_price(self):
        """
        test to set the course price related functionality.
        test al the scenarios for setting a new course price
        """
        set_course_price_url = reverse('set_course_mode_price', kwargs={'course_id': text_type(self.course.id)})
        data = {'course_price': '12%', 'currency': 'usd'}

        # Value Error course price should be a numeric value
        response = self.client.post(set_course_price_url, data)
        self.assertContains(response, "Please Enter the numeric value for the course price", status_code=400)

        # validation check passes and course price is successfully added
        data['course_price'] = 100
        response = self.client.post(set_course_price_url, data)
        self.assertContains(response, "CourseMode price updated successfully")

        course_honor_mode = CourseMode.objects.get(mode_slug='honor')
        course_honor_mode.delete()
        # Course Mode not exist with mode slug honor
        response = self.client.post(set_course_price_url, data)
        self.assertContains(
            response,
            u"CourseMode with the mode slug({mode_slug}) DoesNotExist".format(mode_slug='honor'),
            status_code=400,
        )

    def test_add_coupon(self):
        """
        Test Add Coupon Scenarios. Handle all the HttpResponses return by add_coupon view
        """
        # URL for add_coupon
        add_coupon_url = reverse('add_coupon', kwargs={'course_id': text_type(self.course.id)})
        expiration_date = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=2)

        data = {
            'code': 'A2314', 'course_id': text_type(self.course.id),
            'description': 'ADSADASDSAD', 'created_by': self.instructor, 'discount': 5,
            'expiration_date': '{month}/{day}/{year}'.format(
                month=expiration_date.month, day=expiration_date.day, year=expiration_date.year
            )
        }
        response = self.client.post(add_coupon_url, data)
        self.assertContains(
            response,
            u"coupon with the coupon code ({code}) added successfully".format(code=data['code']),
        )

        #now add the coupon with the wrong value in the expiration_date
        # server will through the ValueError Exception in the expiration_date field
        data = {
            'code': '213454', 'course_id': text_type(self.course.id),
            'description': 'ADSADASDSAD', 'created_by': self.instructor, 'discount': 5,
            'expiration_date': expiration_date.strftime('"%d/%m/%Y')
        }
        response = self.client.post(add_coupon_url, data)
        self.assertContains(
            response,
            "Please enter the date in this format i-e month/day/year",
            status_code=400,
        )

        data = {
            'code': 'A2314', 'course_id': text_type(self.course.id),
            'description': 'asdsasda', 'created_by': self.instructor, 'discount': 99
        }
        response = self.client.post(add_coupon_url, data)
        self.assertContains(
            response,
            u"coupon with the coupon code ({code}) already exist".format(code='A2314'),
            status_code=400,
        )

        response = self.client.post(self.url)
        self.assertContains(response, '<td>ADSADASDSAD</td>')
        self.assertContains(response, '<td>A2314</td>')
        self.assertNotContains(response, '<td>111</td>')

        data = {
            'code': 'A2345314', 'course_id': text_type(self.course.id),
            'description': 'asdsasda', 'created_by': self.instructor, 'discount': 199
        }
        response = self.client.post(add_coupon_url, data)
        self.assertContains(
            response,
            "Please Enter the Coupon Discount Value Less than or Equal to 100",
            status_code=400,
        )

        data['discount'] = '25%'
        response = self.client.post(add_coupon_url, data=data)
        self.assertContains(response, 'Please Enter the Integer Value for Coupon Discount', status_code=400)

        course_registration = CourseRegistrationCode(
            code='Vs23Ws4j', course_id=text_type(self.course.id), created_by=self.instructor,
            mode_slug='honor'
        )
        course_registration.save()

        data['code'] = 'Vs23Ws4j'
        response = self.client.post(add_coupon_url, data)
        msg = u"The code ({code}) that you have tried to define is already in use as a registration code"
        self.assertContains(response, msg.format(code=data['code']), status_code=400)

    def test_delete_coupon(self):
        """
        Test Delete Coupon Scenarios. Handle all the HttpResponses return by remove_coupon view
        """
        coupon = Coupon(
            code='AS452', description='asdsadsa', course_id=text_type(self.course.id),
            percentage_discount=10, created_by=self.instructor
        )

        coupon.save()

        response = self.client.post(self.url)
        self.assertContains(response, '<td>AS452</td>')

        # URL for remove_coupon
        delete_coupon_url = reverse('remove_coupon', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.post(delete_coupon_url, {'id': coupon.id})
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) updated successfully'.format(coupon_id=coupon.id),
        )

        coupon.is_active = False
        coupon.save()

        response = self.client.post(delete_coupon_url, {'id': coupon.id})
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) is already inactive'.format(coupon_id=coupon.id),
            status_code=400,
        )

        response = self.client.post(delete_coupon_url, {'id': 24454})
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) DoesNotExist'.format(coupon_id=24454),
            status_code=400,
        )

        response = self.client.post(delete_coupon_url, {'id': ''})
        self.assertContains(response, 'coupon id is None', status_code=400)

    def test_get_coupon_info(self):
        """
        Test Edit Coupon Info Scenarios. Handle all the HttpResponses return by edit_coupon_info view
        """
        coupon = Coupon(
            code='AS452', description='asdsadsa', course_id=text_type(self.course.id),
            percentage_discount=10, created_by=self.instructor,
            expiration_date=datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=2)
        )
        coupon.save()
        # URL for edit_coupon_info
        edit_url = reverse('get_coupon_info', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.post(edit_url, {'id': coupon.id})
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) updated successfully'.format(coupon_id=coupon.id),
        )
        self.assertContains(response, coupon.display_expiry_date)

        response = self.client.post(edit_url, {'id': 444444})
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) DoesNotExist'.format(coupon_id=444444),
            status_code=400,
        )

        response = self.client.post(edit_url, {'id': ''})
        self.assertContains(response, 'coupon id not found"', status_code=400)

        coupon.is_active = False
        coupon.save()

        response = self.client.post(edit_url, {'id': coupon.id})
        self.assertContains(
            response,
            u"coupon with the coupon id ({coupon_id}) is already inactive".format(coupon_id=coupon.id),
            status_code=400,
        )

    def test_update_coupon(self):
        """
        Test Update Coupon Info Scenarios. Handle all the HttpResponses return by update_coupon view
        """
        coupon = Coupon(
            code='AS452', description='asdsadsa', course_id=text_type(self.course.id),
            percentage_discount=10, created_by=self.instructor
        )
        coupon.save()
        response = self.client.post(self.url)
        self.assertContains(response, '<td>AS452</td>')
        data = {
            'coupon_id': coupon.id, 'code': 'AS452', 'discount': '10', 'description': 'updated_description',
            'course_id': text_type(coupon.course_id)
        }
        # URL for update_coupon
        update_coupon_url = reverse('update_coupon', kwargs={'course_id': text_type(self.course.id)})
        response = self.client.post(update_coupon_url, data=data)
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) updated Successfully'.format(coupon_id=coupon.id),
        )

        response = self.client.post(self.url)
        self.assertContains(response, '<td>updated_description</td>')

        data['coupon_id'] = 1000  # Coupon Not Exist with this ID
        response = self.client.post(update_coupon_url, data=data)
        self.assertContains(
            response,
            u'coupon with the coupon id ({coupon_id}) DoesNotExist'.format(coupon_id=1000),
            status_code=400,
        )

        data['coupon_id'] = ''  # Coupon id is not provided
        response = self.client.post(update_coupon_url, data=data)
        self.assertContains(response, 'coupon id not found', status_code=400)

    def test_verified_course(self):
        """Verify the e-commerce panel shows up for verified courses as well, without Coupons """
        # Change honor mode to verified.
        original_mode = CourseMode.objects.get(course_id=self.course.id, mode_slug='honor')
        original_mode.delete()
        new_mode = CourseModeFactory(
            course_id=six.text_type(self.course.id), mode_slug='verified',
            mode_display_name='verified', min_price=10, currency='usd'
        )
        new_mode.save()

        # Get the response value, ensure the Coupon section is not included.
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        # Coupons should show up for White Label sites with priced honor modes.
        self.assertNotContains(response, 'Coupons List')

    def test_coupon_code_section_not_under_e_commerce_tab(self):
        """
        Test Coupon Creation UI, under E-commerce Tab, should not be available in the Instructor Dashboard with
        e-commerce course
        """
        # Setup e-commerce course
        CourseMode.objects.filter(course_id=self.course.id).update(sku='test_sku')

        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        self.assertNotContains(response, 'Coupon Code List')

    def test_enrollment_codes_section_not_under_e_commerce_tab(self):
        """
        Test Enrollment Codes UI, under E-commerce Tab, should not be available in the Instructor Dashboard with
        e-commerce course
        """
        # Setup e-commerce course
        CourseMode.objects.filter(course_id=self.course.id).update(sku='test_sku')

        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        self.assertNotContains(response, '<h3 class="hd hd-3">Enrollment Codes</h3>')

    def test_enrollment_codes_section_visible_for_non_ecommerce_course(self):
        """
        Test Enrollment Codes UI, under E-commerce Tab, should be available in the Instructor Dashboard with non
        e-commerce course
        """
        response = self.client.get(self.url)
        self.assertContains(response, self.ecommerce_link)
        self.assertContains(response, '<h3 class="hd hd-3">Enrollment Codes</h3>')
