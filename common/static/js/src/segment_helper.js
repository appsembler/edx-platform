(function() {
  'use strict';
  let eventAjaxRequest = function (eventName, postBody) {
    $.ajax({
      url: '/event/' + eventName,
      type: 'POST',
      contentType: 'application/json',
      dataType: 'json',
      data: JSON.stringify(postBody),
      async: true,
      processData: false,
    });
  };

  var SegmentProxy = {
    identify: function () {
      let userId = arguments[0][0];
      let info = arguments[0][1];
      let options = arguments[0][2];

      let postBody = {
        userId: userId,
        info: info,
        options: options
      };
      eventAjaxRequest('identify', postBody);
    },
    page: function (properties) {
      let postBody = {
        info: properties,
      };
      eventAjaxRequest('page', postBody);
    },
    track: function (name, properties) {
      let postBody = {
        name: name,
        info: properties,
      };
      eventAjaxRequest('track', postBody);
    }
  }
  this.SegmentProxy = SegmentProxy;
}).call(this);
