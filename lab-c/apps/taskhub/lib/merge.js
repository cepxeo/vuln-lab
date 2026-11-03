'use strict';
// Recursive object merge used to apply a partial settings patch onto the
// current settings. Objects are merged key by key; scalars overwrite.

function isObject(v) {
  return v && typeof v === 'object' && !Array.isArray(v);
}

function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (isObject(source[key])) {
      if (!isObject(target[key])) target[key] = {};
      deepMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

module.exports = { deepMerge };
