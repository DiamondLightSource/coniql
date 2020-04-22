// This file will measure the performance of the server for web socket subscriptions to SimpleSineWave of various sizes
// And at various frequencies.
// Output is logged to the console.

const { measureSineWave } = require("./measureSineWave");

function printGap() {
  console.log("====================");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

measureSineWave(1, 0.1, 10000)
  .then(() => {
    return measureSineWave(10, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(100, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(1000, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(10000, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(100000, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(1000000, 0.1, 10000);
  })
  .then(() => {
    return measureSineWave(10000000, 0.1, 10000);
  })
  .then(() => {
    process.exit(0);
  });
