;(function (define) {

define([
    'underscore',
    'backbone',
    'js/discovery/models/course_card',
    'js/discovery/models/facet_option',
], function (_, Backbone, CourseCard, FacetOption) {
    'use strict';

    return Backbone.Model.extend({
        url: '/search/course_discovery/',
        jqhxr: null,

        defaults: {
            totalCount: 0,
            latestCount: 0
        },

        initialize: function () {
            this.courseCards = new Backbone.Collection([], { model: CourseCard });
            this.facetOptions = new Backbone.Collection([], { model: FacetOption });
        },

        parse: function (response) {
            var courses = response.results || [];
            var facets = response.facets || {};
            this.courseCards.add(_.pluck(courses, 'data'));

            this.set({
                totalCount: response.total,
                latestCount: courses.length
            });

            var options = this.facetOptions;

            _(facets).each(function (obj, key) {
                _(obj.terms).each(function (count, term) {
                    var fv_display_order = null;
                    if (obj.hasOwnProperty('facet_values')) {
                        fv_display_order = obj.facet_values[term];
                    }

                    options.add({
                        facet: key,
                        term: term,
                        count: count,
                        display_order: obj.display_order,
                        fv_display_order: fv_display_order
                    }, {merge: true});
                });
            });

            options.comparator = function(model) {
                var fv_display_order = model.get('fv_display_order');
                if (fv_display_order) {
                    return [ model.get('display_order'), fv_display_order ];
                } else {
                    return model.get('display_order');
                }
            };

            options.sort();
        },

        reset: function () {
            this.set({
                totalCount: 0,
                latestCount: 0
            });
            this.courseCards.reset();
            this.facetOptions.reset();
        },

        latest: function () {
            return this.courseCards.last(this.get('latestCount'));
        }

    });

});


})(define || RequireJS.define);
