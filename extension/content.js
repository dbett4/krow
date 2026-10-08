// Krow content script — split across krow-core.js + krow-panel.js (see manifest.json).
// Node unit tests require krow-core.js directly.
if (typeof module !== "undefined" && module.exports) {
  module.exports = require("./krow-core.js");
}
