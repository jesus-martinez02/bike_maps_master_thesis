# This file is part of the Demand Generation Tool, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers, Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

# Internal modules
from .io import write_pickle
from .io_osm import all_geometries_from_area
from .logger import log
from .osm_classification import tags_default, data_columns_default, essential_columns, extra_columns, building_threshold_area, default_ignore_tags
from .poi_preprocess import poi_preprocess, construct_building_polygons
from .geometry_utilities import split_by_geometry, polygon_to_centroid
from .poi_categorisation import categorise_residential, categorise_activities
from .poi_visualisation import save_shapefiles
from .settings import proj_crs

# Other packages
import shapely.geometry
import os
from osmnx import geocoder
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np


class POIs:
    """
    This class (POIs) is responsible for downloading, selecting, enhancing and categorizing OSM data in points of
    interest (POIs) categories. When creating the class these methods are run automatically. If inputs would change,
    these procedures can be rerun with the appropriate functions included in this script.

    # Inputs:
    filename: name of the POI class
    city_center: geodataframe containing polygon(s) indicating zones with multi-level and multi-use buildings
    path (optional): path where all things will be saved
    extent: shapely polygon or multipolygon of the study area
    download_tags (optional): only POI with a corresponding tag is downloaded
    ignore_tags (optional): POI info with corresponding tags are dropped from analysis
    POI_columns (optional): columns to keep of the POI data

    # Additional Public attributes:
    folders: cell containing path of all used folders

    # Internal Attributes:
    _redownload_poi: boolean indicating if OSM data should be redownloaded as download_tags might have changed
    _reselect_poi: boolean indicating if POIs needs to be reselected because ignore_tags or POI_columns might be changed
    _preprocess_poi: boolean indicating if POIs needs to be preprocessed when poi again
    _recategorize_poi: boolean indicating if POIs needs to be categorized again
    _recalculate_poi: boolean indicating if POIs needs to be recalculated when poi is asked

    # (Intermediate) outputs:
    OSM_poi: result after poi_download
    poi_selected: result after attribute_selection
    poi_dropped: result after attribute_selection
    poi_points, self.poi_polys: result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
    contour_polys: result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
    no_building_no_contour_polys: result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
    poi_enhanced_buildings: result after preprocessing: enhancing: adding info to building polygons
    categorized_buildings: result (polygon dataframe) after categorizating activity and residential buildings
    categorized_nonbuildings: result (polygon dataframe) after categorizating activity land use
    pois_categorized: result (points) after categorization and conversion into Points
    unconsidered_tags: result after poi_categorization
    """

    def __init__(self, filename: str, extent: (shapely.geometry.Polygon, shapely.geometry.MultiPolygon), download_tags=None, ignore_tags=None,
                 POI_columns=None, city_center=None, path=None, timeout=None):
        """
        filename: name of the POIs class object
        extent: shapely polygon or multipolygon (zones) of the study area
        download_tags (optional): only POI with a corresponding tag is downloaded
        ignore_tags (optional): POI info with corresponding tags are dropped from analysis
        POI_columns (optional): columns to keep of the POI data
        path (optional): path where all things will be saved, default is current path
        """

        self.zones = None # TODO make separate zones object/class with zones gdf, zones id column specified. PA you perform on zones, visualization of zones also easier.
        self.filename = filename
        self.city_center = city_center
        self.path = path
        self.POI_columns = POI_columns
        self.download_tags = download_tags
        self.ignore_tags = ignore_tags
        self.extent = extent
        self.timeout = timeout

        self.OSM_poi, self.crs = None, None # result after poi_download
        self.poi_selected = None  # result after attribute_selection
        self.poi_dropped = None  # result after attribute_selection
        self.poi_points, self.poi_polys = None, None  # result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
        self.contour_polys = None  # result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
        self.no_building_no_contour_polys = None  # result after preprocessing: splitting geometries and removing inconsistencies (contained and overlapping polygons)
        self.poi_enhanced_buildings = None # result after preprocessing: enhancing: adding info to building polygons
        self.categorized_buildings = None # result (polygon dataframe) after categorizating activity and residential buildings
        self.categorized_nonbuildings = None # result (polygon dataframe) after categorizating activity land use
        self.pois_categorized = None  # result (points) after categorization and conversion into Points
        self.unconsidered_tags = None  # result after poi_categorization

        self._redownload_poi = 0
        self._reselect_poi = 0
        self._preprocess_poi = 0
        self._recategorize_poi = 0
        self.calculate_poi()

        log(f'[CREATE] {filename} object created', 20, log_path=self.folders['log'])

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        if filename is None:
            filename = 'POIs'
        self._filename = filename

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        if path is None:
            path = os.getcwd()

        path = os.path.join(path, self.filename)
        self._path = path
        self.folders = {'data': os.path.join(self.path, 'data'),
                        'config': os.path.join(self.path, 'config'),
                        'log': os.path.join(self.path, 'log'),
                        'shapefiles': os.path.join(self.path, 'data', 'shapefiles')}

        # Commented to avoid saving shapefiles
        for v in self.folders.values():
            Path(v).mkdir(parents=True, exist_ok=True)

    @property
    def download_tags(self):
        return self._download_tags

    @download_tags.setter
    def download_tags(self, tags):
        if tags is None:
            tags = tags_default
        self._redownload_poi = 1
        self._recalculate_poi = 1
        self._download_tags = tags

    @property
    def ignore_tags(self):
        return self._ignore_tags

    @ignore_tags.setter
    def ignore_tags(self, tags):
        if tags is None:
            tags = default_ignore_tags

        self._recalculate_poi = 1
        self._reselect_poi = 1

        self._ignore_tags = tags

    @property
    def city_center(self):
        return self._city_center

    @city_center.setter
    def city_center(self, poly):
        self._recategorize_poi = 1
        self._recalculate_poi = 1
        self._city_center = poly

    @property
    def poi_selected(self):
        if not self._reselect_poi:
            return self._poi_selected
        else:
            print("POIs object should be recalculated first.")

    @poi_selected.setter
    def poi_selected(self, poi):
        if poi is None:
            poi = None
        self._poi_selected = poi

    @property
    def poi_dropped(self):
        if not self._reselect_poi:
            return self._poi_dropped
        else:
            print("POIs object should be recalculated first.")

    @poi_dropped.setter
    def poi_dropped(self, poi):
        if poi is None:
            poi = None
        self._poi_dropped = poi

    @property
    def unconsidered_tags(self):
        if not self._reselect_poi:
            return self._unconsidered_tags
        else:
            print("POIs object should be recalculated first.")

    @unconsidered_tags.setter
    def unconsidered_tags(self, tags):
        if tags is None:
            tags = None
        self._unconsidered_tags = tags

    @property
    def POI_columns(self):
        return self._POI_columns

    @POI_columns.setter
    def POI_columns(self, columns):
        """
        If new columns is set, poi must be recalculated
        """
        if columns is None:
            self._POI_columns = data_columns_default
        else:
            # add the essential and extra columns to the given columns
            columns.extend(essential_columns)
            self._POI_columns = list(set(columns))
            columns.extend(extra_columns)
            self._POI_columns = list(set(columns))

        self._recalculate_poi = 1
        self._reselect_poi = 1
        self._redownload_poi = 1
        self._preprocess_poi = 1
        self._recategorize_poi = 1

    @property
    def extent(self):
        return self._extent

    @extent.setter
    def extent(self, extent):
        """
                If new extent is set, poi must be recalculated
         """
        self._recalculate_poi = 1
        self._reselect_poi = 1
        self._redownload_poi = 1
        self._preprocess_poi = 1
        self._recategorize_poi = 1
        # TODO check validity of extent
        self._extent = extent

    @property
    def poi_enhanced_buildings(self):
        if not self._preprocess_poi:
            return self._poi_enhanced_buildings
        else:
            print("POIs object should be recalculated first.")

    @poi_enhanced_buildings.setter
    def poi_enhanced_buildings(self, polys):
        self._poi_enhanced_buildings = polys

    @property
    def contour_polys(self):
        if not self._preprocess_poi:
            return self._contour_polys
        else:
            print("POIs object should be recalculated first.")

    @contour_polys.setter
    def contour_polys(self, polys):
        self._contour_polys = polys

    @property
    def no_building_no_contour_polys(self):
        if not self._preprocess_poi:
            return self._no_building_no_contour_polys
        else:
            print("POIs object should be recalculated first.")

    @no_building_no_contour_polys.setter
    def no_building_no_contour_polys(self, polys):
        self._no_building_no_contour_polys = polys

    @property
    def poi_polys(self):
        if not self._preprocess_poi:
            return self._poi_polys
        else:
            print("POIs object should be recalculated first.")

    @poi_polys.setter
    def poi_polys(self, polys):
        self._poi_polys = polys

    @property
    def poi_points(self):
        if not self._preprocess_poi:
            return self._poi_points
        else:
            print("POIs object should be recalculated first.")

    @poi_points.setter
    def poi_points(self, points):
        self._poi_points = points

    @property
    def categorized_buildings(self):
        if not self._recategorize_poi:
            return self._categorized_buildings
        else:
            print("POIs object should be recalculated first.")

    @categorized_buildings.setter
    def categorized_buildings(self, polys):
        self._categorized_buildings = polys

    @property
    def categorized_nonbuildings(self):
        if not self._recategorize_poi:
            return self._categorized_nonbuildings
        else:
            print("POIs object should be recalculated first.")

    @categorized_nonbuildings.setter
    def categorized_nonbuildings(self, polys):
        self._categorized_nonbuildings = polys

    @property
    def pois_categorized(self):
        if not self._recategorize_poi:
            return self._pois_categorized
        else:
            print("POIs object should be recalculated first.")

    @pois_categorized.setter
    def pois_categorized(self, points):
        self._pois_categorized = points

    def download_poi(self) -> object:
        """
                1. Downloads information from OSM (based on downlaod_tags)

        Returns
        -------
        boolean indicating success of function
        """
        poi = all_geometries_from_area(self.extent, tags=self.download_tags, timeout=self.timeout, select_columns=False)
        log('[DATA] 1. Raw OSM data downloaded', 20, log_path=self.folders['log'])
        self.OSM_poi = poi
        self._redownload_poi = 0

    def calculate_poi(self):
        """
        1. Downloads information from OSM (based on downlaod_tags)
        2. Selects relevant data from OSM (based on POI_columns and ignore_tags)
        3. Cleans and enhances data from OSM
        4. Categorizes data of OSM in residential and activity POIs

        Parameters
        ----------

        Returns
        -------
        boolean indicating success of function
        """
        poi = self.OSM_poi
        if poi is None or self._redownload_poi:
            self.download_poi()
            self.variable_selection()
            self.preprocess_poi()
            self.categorize_poi()
        elif self._reselect_poi:
            self.variable_selection()
            self.preprocess_poi()
            self.categorize_poi()
        elif self._preprocess_poi:
            self.preprocess_poi()
            self.categorize_poi()
        elif self._recategorize_poi:
            self.categorize_poi()

        self._recalculate_poi = 0
        return 1

    def variable_selection(self):
        """
        2. Selects relevant data from OSM (based on POI_columns and ignore_tags)

        Returns
        -------
        boolean indicating success of function

        """
        columns = [col for col in self.POI_columns if col in self.OSM_poi.columns]
        poi = self.OSM_poi.loc[:, columns]  # only store selected columns
        columns_not_in_studyarea = [col for col in self.POI_columns if col not in self.OSM_poi.columns]
        poi[columns_not_in_studyarea] = np.nan

        if not self.ignore_tags:
            self.ignore_tags = default_ignore_tags

        ignore_tags = self.ignore_tags
        self.poi_dropped = poi.loc[(poi["landuse"].isin(ignore_tags["landuse"] + [np.nan])) &
                                   (poi["amenity"].isin(ignore_tags["amenity"] + [np.nan])) &
                                   (poi["leisure"].isin(ignore_tags["leisure"] + [np.nan])) &
                                   (poi["building"].isin(ignore_tags["building"] + [np.nan])) &
                                   (poi["shop"].isna()) & (poi["office"].isna()) & (poi["sport"].isna()) & (poi["tourism"].isna())]


        self.poi_selected = poi.loc[~poi["osmid"].isin(self.poi_dropped["osmid"].to_list())]
        log('[DATA] 2. OSM data selected', 20, log_path=self.folders['log'])
        self._reselect_poi = 0
        return 1

    def preprocess_poi(self):
        """
        3. Preprocesses OSM data: Cleans and enhances data from OSM
            3.1. Inconsistencies removed:
                3.1.1 Contained land-use polygons are split
                3.1.2 Overlapping land-use polygons are split
                3.1.3 Contained building polygons are removed
                3.1.4 Overlapping building polygons are split
            3.2. Extra info is added to building polygons:

        Parameters
        ----------

        Returns
        -------
        boolean indicating success of function
        """

        if self._redownload_poi:
            self.download_poi()
            self.variable_selection()

        if self._reselect_poi:
            self.variable_selection()

        poi = self.poi_selected
                    
                    
        print("Length before poi_preprocess: ",len(self.OSM_poi))

        poi_points, poi_polys, contour_polys, no_building_no_contour_polys = poi_preprocess(poi)
        self.poi_points, self.poi_polys, self.contour_polys, self.no_building_no_contour_polys = poi_points, poi_polys, contour_polys, no_building_no_contour_polys

        log('[DATA] 3. OSM data preprocessed:', 20, log_path=self.folders['log'])
        log('       3.1 OSM data cleaned:', 20, log_path=self.folders['log'])
        log('          3.1.1 Inconsistencies removed', 20, log_path=self.folders['log'])

        self.poi_enhanced_buildings = construct_building_polygons(poi_polys, poi_points)
        log(f'          3.1.2 Buildings < {building_threshold_area} dropped', 20, log_path=self.folders['log'])
        log('[DATA] 3. OSM data preprocessed:', 20, log_path=self.folders['log'])
        log('       3.2 OSM data enhanced: Additional information is added to building polygons', 20, log_path=self.folders['log'])
        self._preprocess_poi = 0
        return 1

    def categorize_poi(self):
        """
        4. Categorizes data of OSM in residential and activity POIs

        Parameters
        ----------

        Returns
        -------
        boolean indicating success of function

        """

        if self._redownload_poi:
            self.download_poi()
            self.variable_selection()
            self.preprocess_poi()
        if self._reselect_poi:
            self.variable_selection()
            self.preprocess_poi()
        if self._preprocess_poi:
            self.preprocess_poi()

        poi_buildings = self.poi_enhanced_buildings
        poi_polys = self.poi_polys

        poi_buildings, unconsidered_residential_tags = categorise_residential(poi_buildings, city_center=self.city_center)
        poi_nonbuilding = poi_polys.loc[~poi_polys['osmid'].isin(poi_buildings['osmid'])]
        poi_building_categorized, poi_nonbuildingleisure_categorized, unconsidered_activity_categories = (
            categorise_activities(poi_buildings, poi_nonbuilding, city_center=self.city_center))
        self.save_shapefile(data=poi_nonbuildingleisure_categorized, filename='poi_nonbuildingleisure_categorized.shp')
        self.save_shapefile(data=poi_building_categorized, filename='poi_building_categorized.shp')

        self.categorized_buildings = poi_building_categorized
        self.categorized_nonbuildings = poi_nonbuildingleisure_categorized

        log('[DATA] 4.1 OSM data categorized: residential and activity categories', 20, log_path=self.folders['log'])

        poi_building_categorized = polygon_to_centroid(poi_building_categorized)
        poi_nonbuildingleisure_categorized = polygon_to_centroid(poi_nonbuildingleisure_categorized)
        log('[DATA] 4.2 OSM data categorized: OSM data converted into POIs', 20, log_path=self.folders['log'])

        unconsidered_tags = {}
        unconsidered_tags["unconsidered_activity_tags"] = unconsidered_activity_categories
        unconsidered_tags["unconsidered_residential_tags"] = unconsidered_residential_tags
        self.unconsidered_tags = unconsidered_tags

        print("If poidpy is applied to a new region, it is recommended you check the unconsidered_tags dictionary. "
              "This dictionary contains tags not taken into account through out the categorization steps in Poidpy.")

        # TODO clean pois_categorized with only columns that are needed
        pois_categorized = pd.concat([poi_building_categorized, poi_nonbuildingleisure_categorized])
        self.pois_categorized = pois_categorized

        self._recategorize_poi = 0
        return 1

    def save_class_object(self):
        write_pickle(self, f'{self.filename}.class', path=self.path)

    def save_shapefile(self, data, filename):
        # return # Avoid saving in shapefiles
        if isinstance(data, gpd.GeoDataFrame):
            for col in data.columns:
                if "outer" in col or "inner" in col:
                    data[col] = data[col].apply(lambda x: ', '.join(x))  # list values cannot be stored in shapefile
            data.to_file(os.path.join(self.folders["shapefiles"], filename))



    def aggregate_over_zones(self, zones: gpd.GeoDataFrame, zone_id_column:str ='ZONENUMMER'):
        """
        Aggregates POIs data into zonal characteristics representing the number of POIs of each type in each zone.

        Parameters
        ----------
        zones: gpd.GeoDataFrame
        zone_id_column: string

        Returns
        -------
        gdf_zones: zones with aggregated info on POIs as new columns

        """
        # TODO columns in aggregate_over_zones hardcoded
        columns_atr = ['School', 'Health', 'Leisure',
                       'Shops', 'Services', 'Industry', 'Catering_industry', 'Tourism',
                       'Others', 'Leisure_area']
        columns_prod = ['large_residential', 'small_residential']
        columns = columns_prod + columns_atr
        gdf_zones = zones.copy()
        for i in columns:
            gdf_zones[i] = 0.0

        pois_categorized = self.pois_categorized.copy()
        crs_poi = pois_categorized.crs.to_epsg()
        crs_zones = gdf_zones.crs.to_epsg()
        if crs_poi != crs_zones:
            pois_categorized = pois_categorized.to_crs(proj_crs)
            gdf_zones = gdf_zones.to_crs(proj_crs)

        pois_categorized = gpd.sjoin(pois_categorized, gdf_zones.loc[:, [zone_id_column, "geometry"]], how='inner', predicate='within',
                                     lsuffix='1', rsuffix='2')
        pois_categorized = pois_categorized.astype({zone_id_column: 'int64'})
        pois_categorized = pois_categorized.drop('index_2', axis=1)
        pois_categorized = pois_categorized.sort_values(zone_id_column)
        gdf_group = pois_categorized.groupby(zone_id_column)
        for ind, gr in gdf_group:
            for col in columns:
                gdf_zones.loc[gdf_zones[zone_id_column] == ind, col] = gr[col].sum()

        gdf_zones['total_activity'] = gdf_zones.loc[:, columns_atr].sum(axis=1)
        gdf_zones['total_residential'] = gdf_zones.loc[:, columns_prod].sum(axis=1)
        gdf_zones = gdf_zones.to_crs(crs_zones)
        self.zones = gdf_zones
        return gdf_zones


def create_POIs_region(region, city_center, path=None, class_name=None, timeout=None, tags=None, selected_columns=None):
    """
    Creates a POIs class object from a given region (string),
    region is a string input to osmnx
    """
    gdf_place = geocoder.geocode_to_gdf(region, which_result=1, buffer_dist=0)
    polygon = gdf_place["geometry"].unary_union
    POIs_obj = POIs(class_name, extent=polygon, city_center=city_center, path=path, timeout=timeout, download_tags=tags, POI_columns=selected_columns)
    POIs_obj.save_class_object()
    return POIs_obj


def create_POIs_osmid(osmid, city_center, path=None, class_name=None, timeout=None, tags=None, selected_columns=None):
    """
    Creates a POIs class object from an osmid (string),
    region is a string input to osmnx
    """
    gdf_place = geocoder.geocode_to_gdf(osmid, which_result=1, buffer_dist=0, by_osmid=True)
    polygon = gdf_place["geometry"].unary_union
    POIs_obj = POIs(class_name, extent=polygon, city_center=city_center, path=path, timeout=timeout, download_tags=tags, POI_columns=selected_columns)
    POIs_obj.save_class_object()
    return POIs_obj


def create_POIs_polygon(extent,  city_center, path=None, class_name=None, timeout=None, tags=None, selected_columns=None):
    """
    Creates a POIs class object from a given extent (polygon),
    extent is a string input to osmnx
    """
    POIs_obj = POIs(class_name, extent=extent, city_center=city_center, path=path, timeout=timeout, download_tags=tags, POI_columns=selected_columns)
    POIs_obj.save_class_object()
    return POIs_obj
