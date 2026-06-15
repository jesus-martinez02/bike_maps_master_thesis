# This file is part of the Demand Generation Tool, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

import json
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, HoverTool
from bokeh.plotting import figure
from bokeh.palettes import brewer, diverging_palette, Category10, Colorblind8
from bokeh.io import export_png
import colorcet as cc
from bokeh.io import show, save
import geopandas as gpd
from .geometry_utilities import split_by_geometry

def get_geodatasource(gdf:gpd.GeoDataFrame):
    """Get getjsondatasource from geopandas object"""
    json_data = json.dumps(json.loads(gdf.to_json()))
    return GeoJSONDataSource(geojson= json_data)


def bokeh_plot_map(gdf:gpd.GeoDataFrame, column=None, title='', highlight_zones=[]):
    """Plot bokeh map from GeoJSONDataSource """

    gdf = gdf.to_crs(epsg=3857)
    if not isinstance(column, type(None)):
        geosource = get_geodatasource(gdf[["geometry", column]])
    else:
        geosource = get_geodatasource(gdf)
    tools = 'wheel_zoom,pan,save,reset'
    # 3857 epsg web mercator
    p = figure(title = title, x_axis_type="mercator", y_axis_type="mercator", height=1000, width=1000,
               toolbar_location='right', tools=tools)
    p.title.text_font_size = '20pt'
    p.add_tile("CartoDB Positron")
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    #Add patch renderer to figure

    if not isinstance(column, type(None)):
        vals = gdf[column].to_list()
        #Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
        if min(vals) >= 0:
            palette = brewer['Greys'][8]
            palette = palette[::-1]
            color_mapper = LinearColorMapper(palette = palette, low = min(vals), high = max(vals))
            color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, height=20, location=(0, 0),
                                 orientation='horizontal', major_label_text_font_size='20px')
        else:
            n = 9
            palette1 = brewer['Blues'][n]
            palette2 = brewer['Oranges'][n]
            midpoint = abs(min(vals))/(abs(min(vals)) + max(vals))
            if midpoint < 0.5:
                try:
                    d_palette = diverging_palette(palette1, palette2, n+round(n*midpoint), midpoint=midpoint)
                except:
                    palette1 = cc.blues
                    palette2 = cc.CET_L18
                    d_palette = diverging_palette(palette1, palette2, n + round(n * midpoint),
                                                  midpoint=midpoint)
            else:
                try:
                    d_palette = diverging_palette(palette1, palette2[0:(round((1-midpoint) * n))+1],  n + round(n * (1-midpoint))-1,
                                                  midpoint=midpoint)
                    d_palette = diverging_palette(palette1, palette2,
                                                  n + round(n * (1 - midpoint)),
                                                  midpoint=midpoint)
                except:
                    palette1 = cc.blues
                    palette2 = cc.CET_L18
                    d_palette = diverging_palette(palette1, palette2,
                                                  n + round(n * (1 - midpoint)) - 1,
                                                  midpoint=midpoint)
            color_mapper = LinearColorMapper(palette = d_palette, low = min(vals), high = max(vals))
            color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, height=20, location=(0, 0),
                                 orientation='horizontal',  major_label_text_font_size='20px')

        p.patches('xs','ys', source=geosource, fill_alpha=1, line_width=0.5, line_color='black',
                  fill_color={'field': column , 'transform': color_mapper})
        p.add_layout(color_bar, 'below')
        TOOLTIPS = [("ZONENUMMER", '@ZONENUMMER'), ("Value", "@" + column)]
        p.add_tools(HoverTool(tooltips=TOOLTIPS))
    else:
        p.patches('xs', 'ys', source=geosource, fill_alpha=0.4, fill_color='grey', line_width=0.5, line_color='black')
        TOOLTIPS = [("ZONENUMMER", '@ZONENUMMER')]
        p.add_tools(HoverTool(tooltips=TOOLTIPS))

    if len(highlight_zones) != 0:
        subsetzones = gdf.loc[gdf.ZONENUMMER.isin(highlight_zones)]
        geosource_subset = get_geodatasource(subsetzones)
        p.patches('xs', 'ys', source=geosource_subset, line_width=2, fill_alpha=0, line_color='black')

    return p


def plot_POIs(zones:gpd.GeoDataFrame, POI_layer:gpd.GeoDataFrame, sample:int=None):

    # Plot: a sample of the classified residential POIs
    p = figure(x_axis_type="mercator", y_axis_type="mercator", height=1000, width=1000)
    # 3857 epsg web mercator
    p.add_tile('CartoDB Positron')

    data = zones.to_crs(epsg=3857)
    geo_source = GeoJSONDataSource(geojson=data.to_json())

    p.patches('xs', 'ys', source=geo_source, line_width=2, fill_alpha=0, line_color='black')
    TOOLTIPS = [("ZONENUMMER", '@ZONENUMMER')]
    p.add_tools(HoverTool(tooltips=TOOLTIPS))

    tmp = POI_layer.to_crs(epsg=3857)
    i = 0
    l = list(tmp['classification'].unique())[::-1]
    for cat in l:
        if isinstance(sample, type(None)):
            tmp1 = tmp[tmp['classification'] == cat]
        else:
            tmp1 = tmp[tmp['classification'] == cat].sample(sample)
        if len (l) <=8:
            tmp1.loc[:, 'color'] = Colorblind8[i]
        else:
            tmp1.loc[:, 'color'] = Category10[len(l)][i]
        geo_source = GeoJSONDataSource(geojson=tmp1.to_json())
        p.circle("x", "y", source=geo_source, fill_alpha=0.1, color='color', legend_label=cat)
        i += 1
    p.legend.click_policy = "hide"
    p.legend.location = "top_right"

    # add a title to your legend
    p.legend.title = "POI categories"
    p.legend.title_text_font_size = "12pt"
    p.legend.title_text_font_style = "normal"

    # change appearance of legend text
    p.legend.label_text_font_size = "12pt"
    p.legend.label_text_font_style = "normal"

    # change background of legend
    p.legend.background_fill_color = "white"
    p.legend.background_fill_alpha = 1

    show(p)


def plot_production(studyarea_zones:gpd.GeoDataFrame):
    p = bokeh_plot_map(studyarea_zones, column="production", title="Production [trips]")
    show(p)
    return p

def plot_attraction(studyarea_zones: gpd.GeoDataFrame):
    p = bokeh_plot_map(studyarea_zones, column="attraction", title="Attraction [trips]")
    show(p)
    return p


def plot_regression_result (studyarea_zones: gpd.GeoDataFrame, result_path=None):
    tmp = studyarea_zones.copy()
    for true, pred in [("production", "prod_pred"), ("attraction", "attr_pred")]:
        if true in tmp.columns and pred in tmp.columns:
            tmp['trip_difference'] = tmp[pred] - tmp[true]
            tmp['percentage_difference'] = tmp['trip_difference']/ tmp[true] * 100
            p = bokeh_plot_map(tmp, column="trip_difference", title=f'{true}: difference (predicted-true)')
            show(p)
            if not isinstance(result_path, type(None)):
                save(p,result_path + '\\' + f'{true}_differenceplot.html')
            p = bokeh_plot_map(tmp, column="percentage_difference", title=f'{true}: percentage difference [%] (predicted-true)')
            show(p)
            if not isinstance(result_path, type(None)):
                save(p,result_path + '\\' + f'{true}_percentagedifferenceplot.html')
            print(
                f"Interactive map created and stored in folder {result_path}")
        else:
                print(f"{true} and {pred} not in columns in GeoDataFrame.")


def save_shapefiles(data, filepaths:list=None):
    # return  # Modification to ommit saving shapefiles
    if isinstance(data, gpd.GeoDataFrame):
        points, poly = split_by_geometry(data, area_pol=False)
        points.to_file(filepaths[0])
        poly.to_file(filepaths[1])

