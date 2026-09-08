"use strict";

const webhook = require("./webhook");
const pira = require("./pira");
const billing = require("./billing");
const outbox = require("./outbox");

module.exports = {
  ...webhook,
  ...pira,
  ...billing,
  ...outbox,
  version: "13-rc2",
  product: "XTC-LIVE",
};
