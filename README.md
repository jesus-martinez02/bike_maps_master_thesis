# Visual Analysis of Bike Mobility Data: Automatic Creation of Bicycle Maps and Main Corridor Identification using Open Data
## Master Thesis 30 ECTS for [KTH MSc Transport and Geoinformation Technology, AH203X Degree Project in Transport Science](https://www.kth.se/en/studies/master/transport-and-geoinformation-technology/msc-transport-and-geoinformation-technology-1.198559). Written at [Institute of Visual Computing, TU Graz](https://ivc.tugraz.at/)

This repository contains the code for the Master Thesis Visual Analysis of Bike Mobility Data: Automatic Creation of Bicycle Maps and Main Corridor Identification using Open Data, written by  Jesús Salvador Martínez Alcaide and supervised by Benedikt Kantz & Tobias Schreck (TU Graz) and Zhenliang Ma (KTH).

The general technological framework used for the development of this thesis is as follows: First, [Python](https://www.python.org/) is used as the main programming language for the main script that automatically generates bicycle maps and contains the model to categorize the importance of different bicycle corridors. Second, OpenStreetMap (OSM) data is fetched with the [Overpass API](https://overpass-api.de/api/) and is stored, processed, and transformed using the geospatial database [PostGIS](https://postgis.net/). Within this database, the [pgRouting](http://pgrouting.org/) extension, which enables network creation and the usage of very fast implementations of routing algorithms, was also used. Additionally, [QGIS](https://qgis.org/) was utilized to better understand and visualize the different geospatial data layers. With respect to the web environment, the toolkit [Bun](https://bun.com/) was utilized. For creating the webmaps, the Open-Source mapping framework [MapLibre](https://maplibre.org/) was employed, using the base maps based on OSM from [Versatiles](https://versatiles.org/). To provide a fast user experience, [Martin](https://martin.maplibre.org/) was used to create a server for vector tiles, and [Nginx](https://nginx.org/) was set up to efficiently cache the tiles and serve the Martin tiles over HTTPS. Finally, to host the created domain, dev.librebikemaps.com, a [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/) was set up, and all the main components of the web were run in different [Docker](containers).

## Instructions for running the code for a new city.

1) Create a .env file with the following fields:
- POSTGRES_DB="your_db"
- POSTGRES_USER="your_user"
- POSTGRES_PASSWORD="your_password"
  
2)) Find the name, administrative_boundary and country tags for the desired city from [OSM](https://www.openstreetmap.org/). This can be done using the "Query Features" capability of OSM, clicking on a point of the city, and finding the relevant OSM feature in the left pane under "Enclosed Features", as shown in the screenshots below.
   
<img width="3664" height="1978" alt="osm_example" src="https://github.com/user-attachments/assets/8e4f62c6-fb63-4e8e-b140-854dbc6cb66b" />
<img width="3664" height="1978" alt="image" src="https://github.com/user-attachments/assets/2e1aadca-1327-4227-a95c-3406d03366aa" />

3) Define a Polygon (in EPSG: 4326) to be the city center area. If not already defined, such a Polygon can be created with tools such as QGIS or online tools such as https://wktmap.com/. Add it to the city_center table, as shown in the exampes in src/python/city_center.sql
   
4) Use the script osm_data.py to fetch the bicycle infrastructure data from Overpass API
5) Run main.py with the names of the selected citie(s). This will create a table, called final_table, with the bicycle network and the percentile of each edge, based on the developed 4-step model for identifying bicycle corridors.
6) Run create_schematic_map.py with the desired city name and percentile, to create a schematic map for this city.

### Other folders included

Other folders included in the repository, not affecting the general workflow to produce maps, but relvant to the thesis are: 
- calibration: Contains the code for calibration of the attraction coefficients based on BiciMad bike-sharing data from the city of Madrid.
- validation: Acquisition and processing of datasets used for evaluation in the cities of Graz, Berlin and Hamburg.
- results: Folder to produce the figures contained in the thesis


