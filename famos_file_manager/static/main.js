/**
 * Constants
 * 
 */
var slidesPerView = 6;
var CHUNK_SIZE = 10000;
var FAMOS_FILES = ['Error_Frames_1.raw', 'X Axis Acceleration.raw',
            'Y Axis Acceleration.raw', 'Z Axis Acceleration.raw'];
var FILE_COUNT = 17;

/**
 * Globals
 * 
 */
var map = null;
var csvFile = null;
var currentLatLng = null;
var imageVehicleSide = null;
var imageVehicleFront= null;
var imageVehicleSteering = null;
var swiper = null;
var folders = [];

var selected = null;

const BEARING_COLUMN = 0;
const HEIGHT_COLUMN = 1;
const LAT_COLUMN = 3
const LONG_COLUMN = 4;
const SPEED_COLUMN = 5;
const TIME_COLUMN = 6;

const X_AXIS = 7;
const Y_AXIS = 8;
const Z_AXIS = 9;

/**
 * Distance between to points
 * 
 * @param {float} lat1 the From Latitude
 * @param {float} lon1 the From Longitude
 * @param {float} lat2 the To Latitude
 * @param {float} lon2 the To Longitude
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
  * @param {float} x 
  * @param {float} y 
  * @param {float} z 
  */
 function calculatePitch(x,y,z) {
    
    return Math.atan2(x, Math.sqrt(y^2+z^2));
 
}

 /**
  * Calculate vehicle roll
  * 
  * @param {float} x 
  * @param {float} y 
  * @param {float} z 
  */
 function calculateRoll(x, y, z) {
    
    return Math.atan2(y, Math.sqrt(x^2+z^2));
 
}

 /**
  * Clear the Canvas
  * 
  * @param {string} containerID the container
  * @param {string} canvasID the canvas to clear
  */
 function clearCanvas(parentID, canvasID) {
    $(`#${canvasID}`).remove(); 
    $(parentID).append(`<canvas id='${canvasID}' width="400" height="110" style="position:absolute; left:0px; right:0px; top:0px; bottom:20px;" />`);
 }

 /**
  * Rotate the image by the specified amount in degrees
  * 
  * @param {object} canvas 
  * @param {object} context 
  * @param {object} image 
  * @param {float} angleInDegrees 
  * 
  */
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
* @param {event} evt the Tab to Show
* @param {string} tab the name of the Tab
* @param {string} button the Tab's button
*/
function showTab(evt, tab, button) {

  inactivateTabs();

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(tab).style.display = "block";
  document.getElementById(button).style.textDecoration = "underline";

  evt.currentTarget.className += " active";

}

/**
 * Build the Menu
 * @param {*} folders the folders to build 
 */
function buildMenu(folders) {
    var htmlFolders = "<a id='clear-folder' onclick='$(this).Clear()')>Clear</a>";

    if (folders.length > 0) {
        htmlFolders += "<hr></hr>";
    }

    var index = 0;

    for (folder in folders) {
        var click = '$(this).Select("' + escape(folders[folder]) + '","' + index + '")'
        var menuID = 'menu-' + folder
        htmlFolders += `<a id='${menuID}' onclick='${click}'> ${folders[folder]}</a>`;
        index += 1;
    }

    $('#dropdown').html(htmlFolders);

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
      if (rows[row][LAT_COLUMN] && rows[row][LONG_COLUMN] && rows[row][LAT_COLUMN] != 0 && rows[row][LONG_COLUMN]) {
          var latlng = [rows[row][LAT_COLUMN], rows[row][LONG_COLUMN]];

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
      iconUrl: startMarker,
      iconSize: [24, 24],
      iconAnchor: [10, 10],
      popupAnchor: [-3, -76]
  });    
  
  var stopIcon = L.icon({
      iconUrl: stopMarker,
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
  var timestamp = null;
  var count = 0;

  for (row in rows) {

      if (rows[row][SPEED_COLUMN] && rows[row][HEIGHT_COLUMN] && rows[row][SPEED_COLUMN] != 0 && rows[row][HEIGHT_COLUMN] != 0) {

          if (latlng) {             
             distanceKms += distance(latlng[0], latlng[1], 
                  parseFloat(rows[row][LAT_COLUMN]),
                  parseFloat(rows[row][LONG_COLUMN]));
             
           }

          if (!timestamp) {
            timestamp = Math.trunc(rows[row][TIME_COLUMN]);
          }

          latlng = [parseFloat(rows[row][LAT_COLUMN]), parseFloat(rows[row][LONG_COLUMN])];
          totalSpeed += parseFloat(rows[row][SPEED_COLUMN]);
          topSpeed = Math.max(parseFloat(rows[row][SPEED_COLUMN]), topSpeed);
          count += 1;

          if (row % modulus == 0 && rows[row][SPEED_COLUMN] != 0 && rows[row][HEIGHT_COLUMN] != 0) {
             dataSpeed.push(rows[row][SPEED_COLUMN]);
             dataHeight.push(rows[row][HEIGHT_COLUMN]);
             var totalSeconds = Math.trunc(rows[row][TIME_COLUMN]) - timestamp;
             var hours = Math.floor(totalSeconds / 3600);
             totalSeconds %= 3600;
             var minutes = Math.floor(totalSeconds / 60);
             seconds = totalSeconds % 60;

             labels.push(hours + ":" + minutes + ":" + seconds);

          }
      }

    }
   
    clearCanvas('#speedFrame', 'speedChart');

    new Chart(document.getElementById("speedChart").getContext('2d'), {
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
   
    clearCanvas('#heightFrame', 'heightChart');

    new Chart( document.getElementById("heightChart").getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
        datasets: [{ 
            data: dataHeight,
            label: "Height in metres",
            borderColor: "#3e95cd",
            fill: false
        }],
        options: {
        title: {
            display: true,
            text: 'Terrain Height above Sea Level'
        }
        }
    }

    });

    $('#details').html('<b>Start Time: </b><p/>' + (new Date(Math.trunc(rows[0][TIME_COLUMN]) * 1000)) +
    '<p/><b>Finish Time: </b><p/>' + (new Date(Math.trunc(rows[count - 1][TIME_COLUMN]) * 1000)) +
    '<p/><b>Average Speed: </b><p/>' + ((totalSpeed/rows.length).toFixed(2)) + "&nbsp;kph" +
    '<p/><b>Top Speed: </b><p/>' + (topSpeed.toFixed(2)) + "&nbsp;kph" +
    '<p/><b>Distance Travelled: </b><p/>' + ((distanceKms).toFixed(2)) + "&nbsp;kms");

}

/**
 * Show the Gauges
 * @param {*} columns 
 * @param {*} rows 
 */
function showGauges(columns, rows) {
    var speedGauge = new RadialGauge({
        renderTo: 'speedGauge',
        width: 200,
        height: 200,
        units: 'Km/h',
        title: false,
        value: 0,
        minValue: 0,
        maxValue: 220,
        majorTicks: [
            '0','20','40','60','80','100','120','140','160','180','200','220'
        ],
        minorTicks: 2,
        strokeTicks: false,
        highlights: [
            { from: 0, to: 50, color: 'rgba(0,255,0,.15)' },
            { from: 50, to: 100, color: 'rgba(255,255,0,.15)' },
            { from: 100, to: 150, color: 'rgba(255,30,0,.25)' },
            { from: 150, to: 200, color: 'rgba(255,0,225,.25)' },
            { from: 200, to: 220, color: 'rgba(0,0,255,.25)' }
        ],
        colorPlate: '#222',
        colorMajorTicks: '#f5f5f5',
        colorMinorTicks: '#ddd',
        colorTitle: '#fff',
        colorUnits: '#ccc',
        colorNumbers: '#eee',
        colorNeedle: 'rgba(240, 128, 128, 1)',
        colorNeedleEnd: 'rgba(255, 160, 122, .9)',
        valueBox: true,
        animationDuration: 100
    }).draw();

    speedGauge.value = 0;
    
    
    var context = $('#pitchView')[0].getContext('2d');
    
    showVehicleOrientation(rows[0]);
    showSteeringOrientation(parseFloat(rows[0][BEARING_COLUMN]));

    $("#range").attr('max', rows.length);
    $("#range").val(0);

    $('#sliderPos').html("<b>Time:</b>&nbsp;" + (new Date(Math.trunc(rows[0][TIME_COLUMN]) * 1000)) + "&nbsp;[0:0:0]");

    var slider = document.getElementById("range");

    let timerId = null;
    var speed = 0;
    var bearing = 0;
    
    slider.oninput = function() {

        if (this.value < rows.length) {
            
            currentLatLng = {
                latitude : rows[this.value][LAT_COLUMN],
                longitude : rows[this.value][LONG_COLUMN]
            };

            var sample = rows.length >= 10000 ? 1000 : 10;

            var totalSeconds = Math.trunc(rows[this.value][TIME_COLUMN]) - Math.trunc(rows[0][TIME_COLUMN]);
            var hours = Math.floor(totalSeconds / 3600);
            totalSeconds %= 3600;
            var minutes = Math.floor(totalSeconds / 60);
            seconds = totalSeconds % 60;

            $('#sliderPos').html("<b>Time:</b>&nbsp;" + (new Date(Math.trunc(rows[this.value][TIME_COLUMN]) * 1000)) + "&nbsp;[" + 
                    hours + ":" + minutes + ":" + seconds + "] - [Observation&nbsp;:&nbsp;" + this.value + "&nbsp;]");

            speed = parseFloat(rows[this.value][SPEED_COLUMN]);
            bearing = parseFloat(rows[this.value][BEARING_COLUMN]);

            if (timerId == null) { 
                timerId = setTimeout(function() {
                    speedGauge.value = speed;
 
                    speedGauge.draw();
                    
                    timerId = null;

                }, 200);
            
            }

            showVehicleOrientation(rows[this.value]);
            showSteeringOrientation(bearing);

        }

    }
    
}

/**
 * The row to process - X,Y,Z readings
 * 
 * @param {integer} row the famos row to process
 * 
 */
function showVehicleOrientation(row) {
    var pitch = calculatePitch(row[X_AXIS], row[Y_AXIS], row[Z_AXIS]);
  
    if (isNaN(pitch)) {
        return;  
    }

    var contextPitch = $('#pitchView')[0].getContext('2d');
    
   showRotatedImage($('#pitchView')[0], contextPitch, imageVehicleSide, pitch * 100);
    $('#pitchLabel').html('<b>Pitch:</b>&nbsp;' + ((pitch * 100).toFixed(3)) + '&deg;');

    var roll = calculateRoll(row[X_AXIS], row[Y_AXIS], row[Z_AXIS]);
    var contextRoll = $('#rollView')[0].getContext('2d');
    
     showRotatedImage($('#rollView')[0], contextRoll, imageVehicleFront, roll * 100);
    $('#rollLabel').html('<b>Roll:</b>&nbsp;' + ((roll * 100).toFixed(3)) + '&deg;');

}

/**
 * The steering position 
 * 
 * @param {integer} integer the steering position
 * 
 */
function showSteeringOrientation(position) {

    if (isNaN(position)) {
        return;  
    }

    var contextSteering = $('#steeringView')[0].getContext('2d');
        
    showRotatedImage($('#steeringView')[0], contextSteering, imageVehicleSteering, position == 0 ? position : 360 - position);
    $('#steeringLabel').html('<b>Position:</b>&nbsp;' + (position.toFixed(3)) + '&deg;');

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
      },   
      2200: {
       slidesPerView: 10,
        spaceBetween: 11
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

function generateSummarySlide(folder, timestamp) {
    var slide = 
    "<div class='swiper-slide' style='border:2px solid #0174DF; background-color: rgba(255,255,255, 0.30);' onclick='showMission(" +
    "\"" + folder + "\",\"" + timestamp + "\");'> " + 
        "<div style='position:absolute; left:3px; top:5px; right:3px;'>" +
        "<div class='play'>" + 
        "<img src='" + playImage + "' style='width:32; height:32px; margin-top:100px;'/></div>" +
        "<table style='color:black;font-family: monospace; font-size: 12px;'>" +
        "<tr><td><label style='color:black;font-family: monospace; font-size: 14px; font-weight:bold'>" +
         (new Date(Math.trunc(timestamp) * 1000)) +
         "</label></td>" +  
        "</tr>" + 
        "</table>" +
        "</div>" +
        "<div style='position:absolute; left:3px; bottom:8px; right:3px; margin-bottom:-5px;'>" + 
            " <label style='color:black;font-family: monospace; font-size: 14px; width:100%; " + 
            " white-space: nowrap; overflow: hidden;text-overflow: ellipsis; display: inline-block;'>" +
            folder + "</label>" +
            "<div id='" + folder + '-' + timestamp + 
            "' style='position:absolute: left:0px; right:0px; bottom:0px; height:5px; margin-bottom:-4px; margin-left:-3px; margin-right:-3px;'><p></p></div>" +
        "</div>" +
    "</div>";

    return slide;

}


function generateStatusSlide(folder, timestamp) {
    var slide = 
    "<div class='swiper-slide' style='border:2px solid #0174DF; background-color: rgba(100, 100, 100, 0.60);'> " + 
        "<div style='position:absolute; left:3px; top:5px; right:3px;'>" +
        "<table style='color:black;font-family: monospace; font-size: 12px;'>" +
        "<tr><td><label style='color:white; font-family: monospace; font-size: 14px; font-weight:bold'>" + 
        (new Date(Math.trunc(timestamp) * 1000)) +
         "</label></td>" +  
        "</tr>" + 
        "</table>" +
        "</div>" +
        "<div style='position:absolute; left:3px; bottom:-10px; right:3px; margin-bottom:-5px;'>" + 
            " <label style='color:white; font-family: monospace; font-size: 14px; width:100%; " + 
            " white-space: nowrap; overflow: hidden;text-overflow: ellipsis; display: inline-block;'>" +
            folder + "</label>" +
            "<div" + 
            "' style='position:absolute: left:0px; right:0px; bottom:0px; height:5px; margin-bottom:-4px; margin-left:-3px; margin-right:-3px;'><p></p></div>" +
        "</div>" +
    "</div>";

    return slide;

}
function generateSwiperEntry(html, folder, filename, timestamp) {

    return html + (filename.startsWith('status') ? generateStatusSlide(folder, timestamp) 
                                                 : generateSummarySlide(folder, timestamp));

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
        
        showGauges(columns, rows);

        console.log('completed conversion');

  }, 100);

}

function displayResults(results, callback) {
  var csv = Papa.parse(results);

  var lines = csv.data;
  var rows = [];
  var columns = null;

  for (var line in lines) {

    if (!columns) {
        columns = lines[line];
        console.log(columns);
    } else {
        rows.push(lines[line]);
    }

  }

  display(columns, rows);

  callback(columns, rows);

}

function setupDisplay() {

    $('#waitDialog').css('display', 'inline-block');

    var parameters = {};

    $.get('/list', parameters, function(data) {
        var html = "";
        var entries = JSON.parse(data)
        var names = [];

        for (entry in entries) {
            html = generateSwiperEntry(html, entries[entry].folder, entries[entry].file_name, entries[entry].timestamp);      
            names.push(entries[entry].folder); 
        }

        $('#swiper-wrapper').html(html);
    
        $('#swiper-container').css('visibility', 'visible');
    
        swiper = createSwipperControl();
    
        $('#swiper-container').css('visibility', 'visible');
    
        folders = [];
        $.each(names, function(i, el){
            if($.inArray(el, folders) === -1) {
                folders.push(el);
            }
        });

        $('#waitDialog').css('display', 'none');

    });

}

function refreshView(callback) {
    var parameters = {};
    var names =[];
    
    $('#waitDialog').css('display', 'inline-block');

    $.get('/list', parameters, function(data) {
        var html = "";
        var entries = JSON.parse(data)
        
        for (entry in entries) {
            html = generateSwiperEntry(html, entries[entry].folder, entries[entry].file_name, entries[entry].timestamp);
            names.push(entries[entry].folder); 
        }       
    
        $('#swiper-wrapper').html(html);
        
        swiper.update();

        folders = [];
        $.each(names, function(i, el){
            if($.inArray(el, folders) === -1) {
                folders.push(el);
            }
        });

        callback();

        $('#waitDialog').css('display', 'none');  

    });

}

function showMission(name, timestamp) {
    var parameters = {
        name: name,
        timestamp: timestamp

    };

    $('#waitDialog').css('display', 'inline-block');

    $.get('/retrieve', parameters, function(data) {

        displayResults(data, function(columns, rows) {

        });

        $('#' + selected).css('background-color', '');
        $('#' + name + '-' + timestamp).css('background-color', 'orange');
        selected =  name + '-' + timestamp;
        $('#waitDialog').css('display', 'none');
    
    });

}

$.fn.Clear = () => {

    $('#folder').text('');

}

$.fn.Select = (folder, index) => {

    $('#folder').text(folder);
  
}

$(document).ready(function() {

    window.onclick = event => {

        if (document.getElementById("dropdown").classList.contains('show')) {
          document.getElementById("dropdown").classList.remove('show');
          document.getElementById("dropdown").classList.toggle("view");
        } else if (document.getElementById("dropdown").classList.contains('view')) {
          document.getElementById("dropdown").classList.remove('view');
        }
      
    }

    imageVehicleSide = new Image();
    imageVehicleSide.src = imageVehicleSideURL;

    imageVehicleFront = new Image();
    imageVehicleFront.src = imageVehicleFrontURL;
 
    imageVehicleSteering = new Image();
    imageVehicleSteering.src = imageVehicleSteeringURL;
 
    $('#folders').bind('click', (e) => {

        buildMenu(folders);

        document.getElementById("dropdown").classList.toggle("show");
        
    });

    $('#refresh').bind('click', (e) => {
        
        refreshView(function() {

        });

    });

    setupDisplay();

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
 
        var zip = JSZip();
        var folder = '';
        
       $('#waitMessage').text('Creating Zip Archive');

        var fileCount = FILE_COUNT;

        for (var iFile = 0; iFile < files.length; iFile++) {   
            var f = files[iFile];

            // Some Filename testing

            if (!f.name.endsWith('.raw')) {
                continue;
            }

            if (f.name.startsWith('GPS.')) {
                fileCount -= 1;
            }
            

            if (FAMOS_FILES.indexOf(f.name) >= 0) {
                fileCount -= 1;
            }

            // Add File to Zip Archive

            zip.file(f.name, f);
   
            if (f.name.startsWith('GPS.time.sec_BUSDAQ')) {
                parts = /_([0-9]*)?(\.raw)/.exec(f.name);
                folder = parts[1];
            }
               
        }

        if (fileCount != 0) {
            alert(`Not all files uploaded - ${fileCount}`);
            return;
        }

        zip.generateAsync({type: "uint8array"}).then(function (data) {
            $('#waitMessage').text('All Files Zipped');
            chunkData(folder, data);
        });

    }

    function chunkData(folder, compressedData) {
        var maxChunks = Math.floor(compressedData.length / CHUNK_SIZE)
  
        $('#waitMessage').text('Chunking Data : ' + compressedData.length);

        sendData(folder, compressedData, maxChunks).then(function(result) {

            var parameters = {
                file_name: result.file_name,
                guid: result.guid,
                folder: folder
            };

            $('#waitMessage').text('Committing Data : ' + compressedData.length);
           
            $.get('/commit', parameters, function(data) {
                
                $('#waitMessage').text('Processing Data : ' + compressedData.length);
                
                $.get('/process', parameters, function(data) {
                   
                    refreshView(function() {
                        $('#waitMessage').text('');
                        $('#waitDialog').css('display', 'none');
                    }); 

                });

            });

        });

    }

    async function sendData(folder, compressedData, maxChunks) {
        var currentChunk = 0;
        var fileName = '';
        var guid = '';
        
        for (var iChunk=0, len = compressedData.length; iChunk<len; iChunk += CHUNK_SIZE) {   
            var chunk = compressedData.slice(iChunk, iChunk + CHUNK_SIZE); 
            var result = await postData(folder, chunk, currentChunk, maxChunks, fileName, guid);

            if (fileName == '') {
                fileName = JSON.parse(result)[0]['file_name'];
                guid = JSON.parse(result)[0]['guid'];
            }
              
            console.log('Uploaded  - ' + currentChunk + "/" + maxChunks + ":" + JSON.parse(result)[0]['file_name']);

            currentChunk += 1;

        }

        return {
            file_name : fileName,
            guid : guid
        };

    }
   
    function postData(folder, chunk, currentChunk, maxChunks, tempFileName, guid) {    
            var zipFile = null;
            var fileName = `chunk_${currentChunk}_${maxChunks}.zip`
   
            try {
                zipFile = new File([chunk], fileName);
            } catch (e) {
                zipFile = new Blob([chunk], fileName); 
            }

            var formData = new FormData();
            formData.append('file_name', tempFileName);
            formData.append('folder', folder);
            formData.append('guid', guid);
            formData.append('chunk', currentChunk);

            formData.append(fileName, zipFile);
        
            return new Promise(resolve => {$.ajax({
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
                                var percentComplete = event.loaded / event.total;                          }
                        }, false);

                        xhr.upload.addEventListener('load', function (event) {
                        }, false);

                        return xhr;

                    },
                    error: function (err) {
                        console.log('Error: [' + err.status + '] - \'' + err.statusText + '\''); 
                        alert('Error: [' + err.status + '] - \'' + err.statusText + '\'');
                        resolve(err);

                    },
                    success: function (result) {  
                        $('#waitMessage').text('Sending  - ' + currentChunk + "/" + maxChunks);
 
                        resolve(result);
     
                    }
                });

            });
        }

    });
