# Generated by Django 1.11.13 on 2018-05-14 20:37


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shoppingcart', '0003_auto_20151217_0958'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoiceitem',
            options={'base_manager_name': 'objects'},
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'base_manager_name': 'objects'},
        ),
    ]
