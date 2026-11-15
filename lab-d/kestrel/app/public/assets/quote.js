// Quote page: partner rate comparison and bulk quotes.
(function () {
  var PARTNER = { name: 'northline', endpoint: 'http://rates.northline.test/v2/rates' };

  function postJson(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (response) { return response.json(); });
  }

  var ratesButton = document.getElementById('partner-rates');
  if (ratesButton) {
    ratesButton.addEventListener('click', function () {
      postJson('/api/v1/rates/sync', { carrier: PARTNER }).then(function (data) {
        document.getElementById('partner-result').textContent =
          data.status === 'ok' ? 'Partner rates loaded.' : 'The partner feed is not reachable right now.';
      });
    });
  }

  var bulkForm = document.getElementById('bulk-form');
  if (bulkForm) {
    bulkForm.addEventListener('submit', function (event) {
      event.preventDefault();
      var parcels = bulkForm.elements.parcels.value.split('\n').map(function (line) {
        var parts = line.split(',');
        return { to: (parts[0] || '').trim(), weight: parseFloat(parts[1]) };
      }).filter(function (parcel) { return parcel.to && !isNaN(parcel.weight); });
      postJson('/api/v1/quote/bulk', { parcels: parcels }).then(function (data) {
        document.getElementById('bulk-result').textContent = (data.quotes || []).map(function (quote) {
          return quote.to + '  ' + quote.weight + ' kg  £' + quote.price.toFixed(2);
        }).join('\n');
      });
    });
  }
})();
