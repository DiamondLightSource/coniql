const { query } = require("graphqurl");

const errorCallback = (error) => {
  console.log("Error:", error);
};

let count = 0;

query({
  query: `subscription {
        subscribeChannel(id: "sim://sinewavesimple(1000,0.1)") {
          id
          value
        }
      }
      `,
  endpoint: "ws://localhost:8000/subscriptions",
  headers: {
    id: 1
  }
})
  .then((observable) => {
    const s = observable.subscribe(
      (event) => {
        // console.log("Event received", event);
        count++;
      },
      (error) => {
        console.log("Error", error);
        // handle error
      }
    );
    return s;
  })
  .then((s) => {
    const t1 = process.hrtime();
    setTimeout(() => {
      s.unsubscribe();
      const t2 = process.hrtime(t1);
      const executionTime = (t2[0] * 1000 + t2[1] / 1000000) / 1000;
      console.log("Unsubbing...");
      console.log(`Final count: ${count}`);
      console.info("Execution time (hr): %ds %dms", t2[0], t2[1] / 1000000);
      console.log(`Execution Time: ${executionTime}`);
      const messageFreq = count / executionTime;
      console.info(`Measured frequency: ${messageFreq} Hz`);
      process.exit(0);
    }, 10000);
  })
  .catch(errorCallback);
