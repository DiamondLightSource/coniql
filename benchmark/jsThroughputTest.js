// This file will measure the performance of the server for web socket subscriptions to SimpleSineWave of various sizes
// And at various frequencies.
// Output is logged to the console.

const { measureSineWave } = require("./measureSineWave");

let frequencies = [];

measureSineWave(100000, 0.1, 10000)
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(200000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(300000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(400000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(500000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(600000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(700000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(800000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(900000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    return measureSineWave(1000000, 0.1, 10000);
  })
  .then((f) => {
    frequencies.push(f);
    frequencies.map((value) => {
      console.log(value);
    });
    process.exit(0);
  });
