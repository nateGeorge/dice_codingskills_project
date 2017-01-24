(function outer(modules, cache, entry) {
  if (typeof Bokeh !== "undefined") {
    var _ = Bokeh._;

    for (var name in modules) {
      Bokeh.require.modules[name] = modules[name];
    }

    for (var i = 0; i < entry.length; i++) {
        var exports = Bokeh.require(entry[i]);

        if (_.isObject(exports.models)) {
          Bokeh.Models.register_locations(exports.models);
        }

        _.extend(Bokeh, _.omit(exports, "models"));
    }
  } else {
    throw new Error("Cannot find Bokeh. You have to load it prior to loading plugins.");
  }
})

({
  "custom/main": [function(require, module, exports) {
    module.exports = {
      models: {
        "FixedTickFormatter": require("custom/fixed_tick_formatter")
      }
    };
  }, {}],
  "custom/fixed_tick_formatter": [function(require, module, exports) {
var FixedTickFormatter, Model, _, p,
  extend = function(child, parent) { for (var key in parent) { if (hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
  hasProp = {}.hasOwnProperty;

_ = require("underscore");

Model = require("model");

p = require("core/properties");

FixedTickFormatter = (function(superClass) {
  extend(FixedTickFormatter, superClass);

  function FixedTickFormatter() {
    return FixedTickFormatter.__super__.constructor.apply(this, arguments);
  }

  FixedTickFormatter.prototype.type = 'FixedTickFormatter';

  FixedTickFormatter.prototype.doFormat = function(ticks) {
    var labels, tick;
    labels = this.get("labels");
    return (function() {
      var i, len, ref, results;
      results = [];
      for (i = 0, len = ticks.length; i < len; i++) {
        tick = ticks[i];
        results.push((ref = labels[tick]) != null ? ref : "");
      }
      return results;
    })();
  };

  FixedTickFormatter.define({
    labels: [p.Any]
  });

  return FixedTickFormatter;

})(Model);

module.exports = {
  Model: FixedTickFormatter
};

}, {}]
}, {}, ["custom/main"]);
