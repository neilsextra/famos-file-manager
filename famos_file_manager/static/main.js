/**
 * Constants
 * 
 */
var slidesPerView = 6;

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
        formData.append('file_' + iFile, files[iFile]);
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
                          percentComplete = parseInt(percentComplete * 100);
                          document.getElementById("uploadProgress").className = "c100 p" + 
                                                                                percentComplete + 
                                                                                " big blue";
                          $('#percentage').html(percentComplete + "%");
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
                $('#waitDialog').css('display', 'none');  

              }
          });
         
      } catch(e) {
          alert(e);
      }
      
  }

});