const { query } = require("graphqurl");
const base64js = require("base64-js");
const assert = require("assert");

const errorCallback = (error) => {
  console.log("Error:", error);
};

// Size in integers, updateTime in seconds, measureTime in milliseconds
function measureSineWave(size, updateTime, measureTime) {
  console.log("--------- Measuring sinewave --------");
  console.log(`Elements: ${size}`);
  console.log(`Update Time: ${updateTime} s`);
  console.log(`Measurement Time: ${measureTime / 1000} s`);

  // Set of numbers to compare incoming data to
  const matchingNumbers = new Set(Array(size).keys());

  let count = 0;

  const q = query({
    query: `subscription {
          subscribeChannel(id: "sim://sinewavesimple(${size},${updateTime})") {
            id
            value {
              base64Array {
                  numberType
                  base64
              }
            }
          }
        }
        `,
    endpoint: "ws://localhost:8080/ws",
    headers: {
      id: size
    }
  })
    .then((observable) => {
      const s = observable.subscribe(
        (event) => {
          // console.log("Event received", event);
          // console.log(event);
          const encodedNumbers =
            event.data.subscribeChannel.value.base64Array.base64;
          const bd = base64js.toByteArray(encodedNumbers);
          const numbers = new Float64Array(bd.buffer);
          // // console.log(numbers);
          try {
            assert(encodedNumbers);
            assert(numbers);
            assert(new Set(numbers).size === matchingNumbers.size);
            assert(numbers.every((x) => matchingNumbers.has(x)));
          } catch (e) {
            console.log("Issue with incoming data");
          }
          // console.log(size);
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

          resolve(messageFreq);
        }, measureTime);
      });
    })
    .catch(errorCallback);

  return q;
}

module.exports.measureSineWave = measureSineWave;
