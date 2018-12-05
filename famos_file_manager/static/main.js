/**
 * Constants
 * 
 */
var slidesPerView = 6;

/**
 * Globals
 * 
 */
var map = null;
var csvFile = null;
var currentLatLng = null;
var imageVehicleSide = null;
var imageVehicleFront= null;

/**
 * Distance between to points
 * 
 * @param {Float} lat1 the From Latitude
 * @param {Float} lon1 the From Longitude
 * @param {Float} lat2 the To Latitude
 * @param {Float} lon2 the To Longitude
 */
function distance(lat1, lon1, lat2, lon2) {
	var radlat1 = Math.PI * lat1/180;
	var radlat2 = Math.PI * lat2/180;
	var theta = lon1-lon2;
	var radtheta = Math.PI * theta/180;
    var dist = Math.sin(radlat1) * Math.sin(radlat2) +
               Math.cos(radlat1) * Math.cos(radlat2) * Math.cos(radtheta);
	if (dist > 1) {
		dist = 1;
	}
    dist = Math.acos(dist)
    
	dist = dist * 180/Math.PI;
    dist = dist * 60 * 1.1515;
    
    return dist * 1.609344;
    
}

/**
 * Get the Central Position within a series of Lats/Longs
 * 
 * @param latLngInDeg array of arrays with latitude and longtitude
 *   pairs in degrees. e.g. [[latitude1, longtitude1], [latitude2
 *   [longtitude2] ...]
 *
 * @return array with the center latitude longtitude pairs in 
 *   degrees.
 */
function getLatLngCenter(latLngInDegr) {
    
    function rad2degr(rad) { 
        return rad * 180 / Math.PI; 
    }

    function degr2rad(degr) { 
        return degr * Math.PI / 180; 
    }

    var LATIDX = 0;
    var LNGIDX = 1;
    var sumX = 0;
    var sumY = 0;
    var sumZ = 0;

    for (var i=0; i<latLngInDegr.length; i++) {
        var lat = degr2rad(latLngInDegr[i][LATIDX]);
        var lng = degr2rad(latLngInDegr[i][LNGIDX]);
        // sum of cartesian coordinates
        sumX += Math.cos(lat) * Math.cos(lng);
        sumY += Math.cos(lat) * Math.sin(lng);
        sumZ += Math.sin(lat);
    }

    var avgX = sumX / latLngInDegr.length;
    var avgY = sumY / latLngInDegr.length;
    var avgZ = sumZ / latLngInDegr.length;

    // convert average x, y, z coordinate to latitude and longtitude
    var lng = Math.atan2(avgY, avgX);
    var hyp = Math.sqrt(avgX * avgX + avgY * avgY);
    var lat = Math.atan2(avgZ, hyp);

    return ([rad2degr(lat), rad2degr(lng)]);

 }

 /**
  * Calculate vehicle pitch
  * @param {Float} x 
  * @param {Float} y 
  * @param {Float} z 
  */
 function calculatePitch(x,y,z) {
    
    return Math.atan2(x, Math.sqrt(y^2+z^2));
 
}

 /**
  * Calculate vehicle roll
  * 
  * @param {Float} x 
  * @param {Float} y 
  * @param {Float} z 
  */
 function calculateRoll(x,y,z) {
    
    return Math.atan2(y, Math.sqrt(x^2+z^2));
 
}

 /**
  * Clear the Canvas
  * 
  * @param {String} containerID the container
  * @param {String} canvasID the canvas to clear
  */
 function clearCanvas(parentID, canvasID) {
    $('#' + canvasID).remove(); 
    $(parentID).append('<canvas id= "'+ canvasID + '" width="400" height="130" style="position:absolute; left:0px; right:0px; top:0px; bottom:0px;" />');

 }

function showRotatedImage(canvas, context, image, angleInDegrees) {
    var angleInRadians = angleInDegrees * (Math.PI/180)
    var x = canvas.width / 2;
    var y = canvas.height / 2;
    var width = image.width;
    var height = image.height;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.translate(x, y);
    context.rotate(angleInRadians);
 
    context.drawImage(image, -width / 2, -height / 2, width, height);
    context.rotate(-angleInRadians);
    context.translate(-x, -y);
    
 }

 function placePin(colour) {
    var icon = L.icon({
        iconUrl:      'icons/' + colour + '.png',  
        iconSize:     [16, 16],
        popupAnchor:  [-3, -76] 
    });

    L.marker([currentLatLng.latitude, currentLatLng.longitude], {icon: icon}).addTo(map);

 }

 /**
  * Inactivate the Tabs
  */
 function inactivateTabs() {
  var iTab, tabcontent, tabbuttons, tablinks;
   
   // Get all elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName("tabcontent");
  for (iTab = 0; iTab < tabcontent.length; iTab++) {
      tabcontent[iTab].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = document.getElementsByClassName("tablinks");
  for (iTab = 0; iTab < tablinks.length; iTab++) {
      tablinks[iTab].className = tablinks[iTab].className.replace(" active", "");
      tablinks[iTab].style.textDecoration = "none";
  }

}

/**
* Show the Active Tab
* 
* @param {*} evt the Tab to Show
* @param {*} tab the name of the Tab
* @param {*} button the Tab's button
*/
function showTab(evt, tab, button) {

  inactivateTabs();

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(tab).style.display = "block";
  document.getElementById(button).style.textDecoration = "underline";

  evt.currentTarget.className += " active";

}

/**
* Show the Map
* @param {*} columns the columns in the data
* @param {*} rows the data rows
*/
function showMap(columns, rows) {
  
  $('#map').css('display', 'none');  

  if (map != null) {

      map.off();
      map.remove();
  }

  var coordinates = [];
  var startLatLng = null;
  var stopLatLng = null;

  for (row in rows) {
      if (rows[row][6] && rows[row][7] && rows[row][6] != 0 && rows[row][7]) {
          var latlng = [rows[row][6], rows[row][7]];

          if (startLatLng == null) {
              startLatLng = latlng;
          }

          stopLatLng = latlng;
          coordinates.push(latlng);

      }

  }
  
  currentLatLng = {
                      latitude: startLatLng[0],
                      longitude: startLatLng[0]

                  };
                  
  var midLatLng = getLatLngCenter(coordinates);

  map = L.map('map', {
      preferCanvas: true
  }).setView([midLatLng[0], midLatLng[1]], 15);

  var startIcon = L.icon({
      iconUrl: 'icons/start-marker.png',
      iconSize: [24, 24],
      iconAnchor: [10, 10],
      popupAnchor: [-3, -76]
  });    
  
  var stopIcon = L.icon({
      iconUrl: 'icons/stop-marker.png',
      iconSize: [24, 24],
      iconAnchor: [20, 20],
      popupAnchor: [-3, -76]
  });

  L.marker(startLatLng, {icon: startIcon}).addTo(map);
  L.marker(stopLatLng, {icon: stopIcon}).addTo(map);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 30,
  minZoom: 9,
  noWrap:true
  }).addTo(map);

  var options = {}

  L.polyline(
      coordinates,
      {
          color: 'blue',
          weight: 2,
          opacity: .7,
          lineJoin: 'round'
      }
  ).addTo(map);

  setTimeout(function() {
      map.invalidateSize();
      $('#map').css('display', 'inline-block');

      setTimeout(function() {
          map.invalidateSize();
      }, 500);
  }, 100);

  window.addEventListener("resize", function() {
     map.invalidateSize();      
  });

  $('.leaflet-control-attribution').hide();
  
}

/**
* Show the Charts
* 
* @param {*} columns 
* @param {*} rows 
*/
function showCharts(columns, rows) {
  var dataSpeed = [];
  var dataHeight = [];
  var labels = [];

  var length = rows.length;
  var modulus = length >= 100000 ? 1000 : length >= 10000 ? 100 : 1;
  var totalSpeed = 0.0;

  var distanceKms = 0;
  var latlng = null;
  var topSpeed = 0.0;
  var startTime = null;
  var count = 0;

  for (row in rows) {

      if (rows[row][11] && rows[row][12] && rows[row][11] != 0 && rows[row][11] != 0) {

          if (latlng) {             
             distanceKms += distance(latlng[0], latlng[1], 
                  parseFloat(rows[row][6]),
                  parseFloat(rows[row][7]));
             
           }

          if (!startTime) {
              startTime = Math.trunc(rows[row][12]);
          }

          latlng = [parseFloat(rows[row][6]), parseFloat(rows[row][7])];
          totalSpeed += parseFloat(rows[row][11]);
          topSpeed = Math.max(parseFloat(rows[row][11]), topSpeed);
          count += 1;

          if (row % modulus == 0 && rows[row][11] != 0 && rows[row][4] != 0) {
             dataSpeed.push(rows[row][11]);
             dataHeight.push(rows[row][4]);
             var totalSeconds = Math.trunc(rows[row][12]) - startTime;
             var hours = Math.floor(totalSeconds / 3600);
             totalSeconds %= 3600;
             var minutes = Math.floor(totalSeconds / 60);
             seconds = totalSeconds % 60;

             labels.push(hours + ":" + minutes + ":" + seconds);

          }
      }

  }
   
    clearCanvas('#speedFrame', 'speedChart');
    
    var ctx = document.getElementById("speedChart").getContext('2d');

    new Chart(ctx, {
      type: 'line',
      data: {
          labels: labels,
       datasets: [{ 
          data: dataSpeed,
          label: "Speed in Kmh",
          borderColor: "#3e95cd",
          fill: false
    }],
    options: {
      title: {    
        display: true,
        text: 'Speed of Vehicle'
      }
    }
  }
  }); 
   
}

/**
 * Create a swiper control
 * @return the newly constructed swiper control
 * 
 */
function createSwipperControl() {

  var swiper = new Swiper('.swiper-container', {
    slidesPerView: slidesPerView,
    centeredSlides: false,
    spaceBetween: 10,
    breakpointsInverse: true,
    breakpoints: {
      200: {
        slidesPerView: 1,
        spaceBetween: 10
      },
      600: {
        slidesPerView: 2,
        spaceBetween: 10
      },    
      800: {
        slidesPerView: 3,
        spaceBetween: 10
      },    
      1000: {
        slidesPerView: 4,
        spaceBetween: 10
      },
      1200: {
        slidesPerView: 5,
        spaceBetween: 10
      },    
      1400: {
        slidesPerView: 6,
        spaceBetween: 10
      },   
      1600: {
        slidesPerView: 7,
        spaceBetween: 10
      },
      1800: {
        slidesPerView: 8,
        spaceBetween: 10
      },
      2000: {
        slidesPerView: 9,
        spaceBetween: 10
      }
    },
    pagination: {
      el: '.swiper-pagination',
      clickable: true,
    },
    navigation: {
      nextEl: '.swiper-button-next',
      prevEl: '.swiper-button-prev',
    },

  });

  return swiper;

}

function display(columns, rows) {

  showMap(columns, rows);

  window.setTimeout(() => {

      inactivateTabs();

      $('#display').css('display', 'inline-block');
      $('#structureFrame').css('display', 'inline-block');
      $('#tab1').css('text-decoration', 'underline');
      $('#tab1').addClass('active');

      showCharts(columns, rows);
      
      console.log('completed conversion');

  }, 100);

}

function displayResults(results) {
  var csv = Papa.parse(results);

  var lines = csv.data;
  var rows = [];
  var columns = null;

  for (var line in lines) {

    if (!columns) {
         columns = lines[line];
    } else {
         rows.push(lines[line]);
    }

  }

  display(columns, rows);

}

$(document).ready(function() {

  createSwipperControl();

  var dropzone = $('#droparea');

  dropzone.on('dragover', function() {
    dropzone.addClass('hover');
    return false;
  });

  dropzone.on('dragleave', function() {
    dropzone.removeClass('hover');
    return false;
  });
  
  dropzone.on('drop', function(e) {
    e.stopPropagation();
    e.preventDefault();
    dropzone.removeClass('hover');
   
    //retrieve uploaded files data
    var files = e.originalEvent.dataTransfer.files;
    processFiles(files);
    
    return false;

  });
  
  var uploadBtn = $('#uploadbtn');
  var defaultUploadBtn = $('#upload');
 
  uploadBtn.on('click', function(e) {
    e.stopPropagation();
    e.preventDefault();
    defaultUploadBtn.click();
  });

  defaultUploadBtn.on('change', function() {
    var files = $(this)[0].files;

    processFiles(files);

    return false;

  });  

  function processFiles(files) {
    $('#waitDialog').css('display', 'inline-block');

    try {         
      var formData = new FormData();
  
      for (var iFile = 0; iFile < files.length; iFile++) {
        formData.append(files[iFile].name, files[iFile]);
      }

      $.ajax({
          url: '/upload',
          type: 'POST',
          maxChunkSize: 10000,
          contentType: false,
          processData: false,
          async: true,
          data: formData,
              xhr: function() {
                  var xhr = $.ajaxSettings.xhr();

                  xhr.upload.addEventListener('progress', function (event) {
                       if (event.lengthComputable) {
                          var percentComplete = event.loaded / event.total;
                       }
                      
                  }, false);

                  xhr.upload.addEventListener('load', function (event) {
                      $('#percentage').html('Loaded');                        
                 }, false);

                  return xhr;

              },
              error: function (err) {
                  $('#waitDialog').css('display', 'none');  
                  
                  alert('Error: [' + err.status + '] - \'' + err.statusText + '\'');

                  var notification = new Notification("Error in upload", {
                      dir: "auto",
                      lang: "",
                      body:'Error: [' + err.status + '] - \'' + err.statusText + '\'',
                      tag: "Upload Error"

                  });
              },
              success: function (result) {  
                
                displayResults(result);

                $('#waitDialog').css('display', 'none');  

              }
          });
         
      } catch(e) {
          alert(e);
      }
      
  }

});