window.addEventListener('beforeunload', (event) => {
  // Cancel the event as stated by the standard.
  event.preventDefault();
 
});
var geojsonFormat = new ol.format.GeoJSON();

var raster = new ol.layer.Tile({
    source: new ol.source.XYZ({
      url: `https://mt0.google.com/vt/lyrs=y&x={x}&y={y}&z={z}`
  })
  });


  var source = new ol.source.Vector({wrapX: false});

  var vector = new ol.layer.Vector({
    source: source
  });

  var photoImag =  new ol.layer.Image({
   
  })

  var map = new ol.Map({
    layers: [raster, photoImag,vector],
    target: 'map',
    view: new ol.View({
        projection:'EPSG:4326',
      center: [73.97718394780678, 18.50668301348885],
      zoom: 17
    })
  });

  var typeSelect = document.getElementById('type');

  var draw  = new ol.interaction.Draw({
        source: source,
        type: 'Polygon'
      });
      map.addInteraction(draw);
    
  


  /**
   * Handle change event.
   */
draw.on('drawstart', function (){
    source.clear()
})

function getDates(){
    feat = source.getFeatures()[0]
    var geojson = geojsonFormat.writeFeature(feat);

    fetch(`http://127.0.0.1:8000/dates/?polygon=${JSON.stringify(JSON.parse(geojson).geometry)}`)
    .then(res => res.json())
    .then(data => {
        sel = document.getElementById('Dates')
        
        data.forEach(element => {
        op = document.createElement('option')
        op.innerHTML = element.date 
        op.value = element.date
        sel.appendChild(op)
        });
        console.log(data)})
}

const ctx = document.getElementById("myChart").getContext("2d");
        const myLineChart = new Chart(ctx, {
            type: "line",
            // data: initialData,
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

function getStats() {
  feat = source.getFeatures()[0]
    var geojson = geojsonFormat.writeFeature(feat);
    var start_date = document.getElementById('start').value
    var end_date = document.getElementById('end').value

    fetch(`http://127.0.0.1:8000/ndvi-stats/?polygon=${JSON.stringify(JSON.parse(geojson).geometry)}&start_date=${start_date}&end_date=${end_date}`)
    .then(res => res.json())
    .then(data => {
      const config = {
        type: 'line',
        data: data,
      };
      alldata = data.stats[0].data
      label = []
      list = []
      alldata.forEach(ele => {
        label.push(ele.interval.from)
        list.push(ele.outputs.data.bands.B0.stats.mean)
      })
      var chartData = {
        labels: label,
        datasets: [{
          label: 'Stats',
          data: list,
          fill: false,
          borderColor: 'rgb(75, 192, 192)',
          tension: 0.1
        }]
      };
      myLineChart.data = chartData;
      myLineChart.update();
      })
}

function getImages(e) {
  
  feat = source.getFeatures()[0]
  var geojson = geojsonFormat.writeFeature(feat);
  var extent = feat.getGeometry().getExtent();
  var date = document.getElementById('Dates').value
  var index = document.getElementById('Index').value
  fetch(`http://127.0.0.1:8000/imagery/?bbox=${JSON.stringify(extent)}&polygon=${JSON.stringify(JSON.parse(geojson).geometry)}&index=${index}&date=${date}`)
  .then(res => res.json())
  .then(data => {
    console.log(data)
    imgsource = new ol.source.ImageStatic({
    url: `http://127.0.0.1:8000/${data.path}`,
    // url : 'http://127.0.0.1:8000/imagery/?polygon=%7B%22type%22%3A%22Polygon%22%2C%22coordinates%22%3A%5B%5B%5B70.91293394565582%2C21.012296676635742%5D%2C%5B70.91121196746826%2C20.99965274333954%5D%2C%5B70.92491805553436%2C20.99965274333954%5D%2C%5B70.91293394565582%2C21.012296676635742%5D%5D%5D%7D&index=ndvi&date=2023-10-07',
    imageExtent: extent
  })
  photoImag.setSource(imgsource)
  })
  

}