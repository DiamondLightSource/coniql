const { query } = require("graphqurl");

const errorCallback = (error) => {
  console.log("Error:", error);
};

// Size in integers, updateTime in seconds, measureTime in milliseconds
function measureSineWave(size, updateTime, measureTime) {
  console.log("--------- Measuring sinewave --------");
  console.log(`Elements: ${size}`);
  console.log(`Update Time: ${updateTime} s`);
  console.log(`Measurement Time: ${measureTime / 1000} s`);

  let count = 0;

  const q = query({
    query: `subscription {
          subscribeChannel(id: "sim://sinewavesimple(${size},${updateTime})") {
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
      // Forces extra .then to wait until completion
      return new Promise((resolve) => {
        setTimeout(() => {
          s.unsubscribe();
          const t2 = process.hrtime(t1);
          const executionTime = (t2[0] * 1000 + t2[1] / 1000000) / 1000;
          console.log(`Final count: ${count}`);
          console.log(`Execution Time: ${executionTime}`);
          const messageFreq = count / executionTime;
          console.info(`Measured frequency: ${messageFreq} Hz`);

          resolve();
        }, measureTime);
      });
    })
    .catch(errorCallback);

  return q;
}

module.exports.measureSineWave = measureSineWave;
