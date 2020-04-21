const { query } = require("graphqurl");

function eventCallback(event) {
  console.log("Event received:", event);
  // handle event
}

function errorCallback(error) {
  console.log("Error:", error);
}

query(
  {
    query: `subscription {
        subscribeChannel(id: "sim://sinewavesimple(1000,0.1)") {
          id
          value
        }
      }
      `,
    endpoint: "ws://localhost:8000/subscriptions"
  },
  eventCallback,
  errorCallback
);
