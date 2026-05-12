// LoRa Tracker — frontend logic
// RX_LAT and RX_LNG are injected by templates/index.html

var map = L.map('map').setView([window.RX_LAT, window.RX_LNG], 13);

// Offline-capable tile layer — caches tiles in IndexedDB automatically
var tileLayer = L.tileLayer.offline('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: 'OpenStreetMap',
  maxZoom: 19,
  minZoom: 5
});
tileLayer.addTo(map);

// Control bar: lets user save tiles for current view for offline use
var controlSaveTiles = L.control.savetiles(tileLayer, {
  zoomlevels: [13, 14, 15],   // zoom levels to cache around current view
  confirm: function(layer, successCallback) {
    if (window.confirm('Save map tiles for offline use?')) successCallback();
  },
  confirmRemoval: function(layer, successCallback) {
    if (window.confirm('Remove all saved tiles?')) successCallback();
  },
  saveText: '💾 Save tiles',
  rmText: '🗑️ Clear tiles'
});
controlSaveTiles.addTo(map);

// Show status banner when tiles load from cache vs network
tileLayer.on('tilesaved', function(e) {
  console.log('Tiles saved to offline cache:', e.lengthSaved);
});
tileLayer.on('tileerror', function() {
  if (!document.getElementById('map-offline-banner')) {
    var banner = document.createElement('div');
    banner.id = 'map-offline-banner';
    banner.style.cssText = 'position:absolute;top:60px;left:50%;transform:translateX(-50%);' +
      'background:#f39c12;color:white;padding:10px 20px;border-radius:5px;z-index:1000;' +
      'font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,0.3)';
    banner.textContent = '⚠️ No internet — using cached tiles. Markers still work.';
    document.getElementById('map').appendChild(banner);
  }
});

var txIcon = L.divIcon({ className:'',
  html:'<div style="background:#e74c3c;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

var rxIcon = L.divIcon({ className:'',
  html:'<div style="background:#3498db;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

L.marker([window.RX_LAT, window.RX_LNG], {icon: rxIcon})
  .addTo(map)
  .bindPopup('<b>Receiver (fixed)</b><br>Lat: ' + window.RX_LAT + '<br>Lng: ' + window.RX_LNG);

var txMarker   = null;
var roadLayer  = null;
var lineLayer  = null;
var histLayer  = null;

var showRoad     = true;
var showStraight = true;
var showHistory  = true;

var lastRouteCalcLat = null;
var lastRouteCalcLng = null;

function haversine(lat1, lng1, lat2, lng2, unit) {
  var R = (unit === 'km') ? 6371 : 6371000; // Earth radius in km or meters
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLng = (lng2 - lng1) * Math.PI / 180;
  var a = Math.sin(dLat/2)*Math.sin(dLat/2) +
          Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*
          Math.sin(dLng/2)*Math.sin(dLng/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function shouldRecalculateRoute(lat, lng) {
  if (lastRouteCalcLat === null || lastRouteCalcLng === null) {
    return true; // First calculation
  }
  var distance = haversine(lastRouteCalcLat, lastRouteCalcLng, lat, lng, 'meters');
  return distance > 5; // Recalculate if moved more than 5 meters
}

function toggleLayer(type) {
  if (type === 'road') {
    showRoad = !showRoad;
    document.querySelector('.btn-road').classList.toggle('active', showRoad);
    if (roadLayer) { showRoad ? roadLayer.addTo(map) : map.removeLayer(roadLayer); }
  } else if (type === 'straight') {
    showStraight = !showStraight;
    document.querySelector('.btn-straight').classList.toggle('active', showStraight);
    if (lineLayer) { showStraight ? lineLayer.addTo(map) : map.removeLayer(lineLayer); }
  } else if (type === 'history') {
    showHistory = !showHistory;
    document.querySelector('.btn-history').classList.toggle('active', showHistory);
    if (histLayer) { showHistory ? histLayer.addTo(map) : map.removeLayer(histLayer); }
  }
}

function recalcRoute() {
  fetch('/route').then(r => r.json()).then(d => {
    if (d.error) {
      document.getElementById('r-steps').innerHTML = '<li>' + d.error + '</li>';
      document.getElementById('r-dist').textContent = '--';
      document.getElementById('r-time').textContent = '--';
      return;
    }
    document.getElementById('r-dist').textContent = d.distance;
    document.getElementById('r-time').textContent = d.duration;
    var html = d.steps.map((s,i) => '<li>' + (i+1) + '. ' + s + '</li>').join('');
    document.getElementById('r-steps').innerHTML = html || '<li>Route found</li>';

    if (roadLayer) map.removeLayer(roadLayer);
    if (d.geometry && d.geometry.length > 0) {
      roadLayer = L.polyline(d.geometry, {color:'#1D9E75', weight:4, opacity:.85});
      if (showRoad) roadLayer.addTo(map);
    }

    // Save position for next comparison
    if (d.tx_lat !== undefined && d.tx_lng !== undefined) {
      lastRouteCalcLat = d.tx_lat;
      lastRouteCalcLng = d.tx_lng;
    }
  }).catch(e => {
    document.getElementById('r-steps').innerHTML = '<li>Route error: ' + e + '</li>';
  });
}

function updateStraightLine(txLat, txLng) {
  if (lineLayer) map.removeLayer(lineLayer);
  var dist = haversine(txLat, txLng, window.RX_LAT, window.RX_LNG, 'km');
  var distStr = dist >= 1 ? dist.toFixed(1) + ' km' : (dist*1000).toFixed(0) + ' m';
  document.getElementById('r-line').textContent = distStr;
  lineLayer = L.polyline([[txLat, txLng],[window.RX_LAT, window.RX_LNG]],
    {color:'#E08020', weight:2.5, dashArray:'10,6', opacity:.8});
  if (showStraight) lineLayer.addTo(map);
}

function updateHistory(points) {
  if (histLayer) map.removeLayer(histLayer);
  if (points.length < 2) return;
  var latlngs = points.map(p => [p[0], p[1]]);
  histLayer = L.polyline(latlngs,
    {color:'#378ADD', weight:3, dashArray:'1,8', lineCap:'round', opacity:.7});
  if (showHistory) histLayer.addTo(map);
  document.getElementById('c-pts').textContent = points.length;
  document.getElementById('hist-info').textContent =
    'GPS track history: ' + points.length + ' points recorded';
}

function update() {
  fetch('/data').then(r => r.json()).then(d => {
    document.getElementById('c-lat').textContent  = d.lat  || '--';
    document.getElementById('c-lng').textContent  = d.lng  || '--';
    document.getElementById('c-msg').textContent  = d.msg;
    document.getElementById('c-rssi').textContent = d.rssi !== 'N/A' ? d.rssi + ' dBm' : '--';
    document.getElementById('c-seq').textContent  = (d.seq !== null && d.seq !== undefined) ? d.seq : '--';
    document.getElementById('c-drop').textContent = d.dropped || 0;
    document.getElementById('last-update').textContent =
      'Last update: ' + new Date().toLocaleTimeString();

    if (d.lat && d.lng) {
      var lat = parseFloat(d.lat), lng = parseFloat(d.lng);
      var latlng = [lat, lng];
      if (!txMarker) {
        txMarker = L.marker(latlng, {icon: txIcon}).addTo(map)
          .bindPopup('<b>Transmitter (live GPS)</b><br>' + d.msg);
        map.setView(latlng, 13);
        recalcRoute(); // First route calculation
      } else {
        txMarker.setLatLng(latlng).setPopupContent('<b>Transmitter (live GPS)</b><br>' + d.msg);
        // Only recalculate if position changed significantly
        if (shouldRecalculateRoute(lat, lng)) {
          recalcRoute();
        }
      }
      updateStraightLine(lat, lng);
    }
  });

  fetch('/history').then(r => r.json()).then(d => {
    updateHistory(d.points);
  });
}

setInterval(update, 3000);
update();
