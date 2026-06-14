import numpy as np
from .osm_classification import building_residential_max_area, activity_categories, landuse_based_activity_categories, \
    essential_columns, extra_columns, non_building_activity_categories
from .geometry_utilities import contains_polygon
import geopandas as gpd


def categorise_residential(poi_building, city_center=None):
    # adds large residential and small residential to polygons based on rules
    # value is in m²

    print("3. Categorizing residential buildings.")

    # init residential
    poi_building['large_residential'] = 0.0 # Changed by Jesus
    poi_building['small_residential'] = 0.0 # Changed by Jesus



    indexes_loop = np.full(len(poi_building), False)

    # for the purpose of saving poi_building as shapefile
    # tmp = poi_building.copy(deep=True)
    # for col in ['landuse_outer', 'shop_outer',
    #             'tourism_outer', 'sport_outer', 'office_outer', 'amenity_outer',
    #             'leisure_outer', 'shop_inner_poly', 'tourism_inner_poly',
    #             'sport_inner_poly', 'office_inner_poly', 'amenity_inner_poly',
    #             'leisure_inner_poly', 'building_inner_point', 'shop_inner_point',
    #             'tourism_inner_point', 'sport_inner_point', 'office_inner_point',
    #             'amenity_inner_point', 'leisure_inner_point']:
    #     tmp[col] = tmp[col].apply(lambda x: ", ".join(x))

    # clear small residential buildings
    tag_dic = {'building': ["house", "semidetached_house", "terrace", "farm", "detached", "home", 'houseboat', 'villa']}
    indexes = _indexes_tagged(poi_building, tag_dic)
    poi_building.loc[indexes, 'small_residential'] = 1
    indexes_loop = indexes | indexes_loop

    # clear large residential buildings
    tag_dic = {'building': ['apartments', 'dormitory', 'student_accomodation'], 'amenity':['student_accomodation']}
    indexes = _indexes_tagged(poi_building, tag_dic)
    poi_building.loc[indexes, 'large_residential'] = 1
    indexes_loop = indexes | indexes_loop

    tag_dic = {'building': ['residential']}
    indexes = _indexes_tagged(poi_building, tag_dic)
    if city_center is not None:
        indexes_yes = indexes & poi_building.loc[indexes, "geometry"].within(
            city_center["geometry"].unary_union)  # inside city center
        indexes_no = indexes & ~(poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union))
        poi_building.loc[indexes_no, 'small_residential'] = 1
        poi_building.loc[indexes_no, 'large_residential'] = 0
        poi_building.loc[indexes_yes, 'large_residential'] = 1
        poi_building.loc[indexes_yes, 'small_residential'] = 0
    else:
        poi_building.loc[indexes, 'small_residential'] = 1
        poi_building.loc[indexes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # more than 50% of buildings in Leuven case study already classified after these steps

    # clear no residential function
    tag_dic = {'building': ['industrial', 'church', 'chapel', 'school', 'barn', 'brewery', 'cloister', 'college', 'parish_hall',
                            'warehouse', 'town_hall', 'library', 'farm_auxiliary', 'government', 'hospital', 'hotel',
                            'kindergarten', 'monastery', 'mosque', 'museum', 'public', 'ruins', 'sports_centre',
                            'sports_hall', 'stadium', 'train_station', 'transportation', 'university', 'hut',
                            'pavilion', "construction", "hangar"],
               'amenity': ['university', 'community_centre', 'social_facility', 'place_of_worship', 'music_school',
                           'school', 'kindergarten', 'fuel', 'clinic', 'events_venue', 'townhall', 'bus_station',
                           'monastery', 'parking', 'hospital', 'shelter', 'prison', 'theatre'],
               'leisure': ['sports_centre', 'stadium', 'pitch', 'play_ground'],
               'office': ['government'],
               'tourism': ['hotel', 'hostel']}
    # university sometimes also dorms but mostly not
    indexes = _indexes_tagged(poi_building, tag_dic)

    for key in tag_dic.keys():
        if key != 'building':
            indexes = indexes | poi_building[key + "_inner_poly"].apply(lambda x: any(value in x for value in tag_dic[key]))
        indexes = indexes | poi_building[key + "_inner_point"].apply(lambda x: any(value in x for value in tag_dic[key]))
    indexes = indexes & (~indexes_loop)  # because building can be dormitory with university point inside ==> already
    # classified as residential so do not overwrite here.
    poi_building.loc[indexes, 'small_residential'] = 0
    poi_building.loc[indexes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # polygons in non-residential landuse and contours
    tag_dic_non_residential_landuse_contour = {"amenity_outer": "all",  # but not empty
                                               'tourism_outer': "all",
                                               'shop_outer': "all",
                                               'sport_outer': "all",
                                               'leisure_outer': "all"  # garden polygon too big aan Heverlee Colruyt
                                               }
    indexes = _indexes_tagged(poi_building, tag_dic_non_residential_landuse_contour)
    indexes = indexes | (poi_building["landuse_outer"].apply(
        lambda x: any(lu in x for lu in ['industrial', 'military', 'construction', 'cemetery', 'railway',
                                         'recreation_ground', 'orchard', 'depot', 'landfill', 'education'])))
    indexes = indexes & (~indexes_loop)
    poi_building.loc[indexes, 'small_residential'] = 0
    poi_building.loc[indexes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # priority != building and unlikely_residential lu:
    unlikely_residential_landuse = ['retail', 'commercial', 'forest', 'farmyard', 'farmland']
    indexes = (poi_building["landuse_outer"].apply(lambda x: any(lu in x for lu in unlikely_residential_landuse))) \
              & (poi_building['priority'] != 'building') \
              & (~indexes_loop)
    poi_building.loc[indexes, 'small_residential'] = 0
    poi_building.loc[indexes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # polygons with priority != building and in residential_landuse
    indexes = (poi_building["landuse_outer"].apply(lambda x: 'residential' in x)) \
              & (poi_building['priority'] != 'building') \
              & (~indexes_loop)

    indexes_yes = indexes & (poi_building["polygon_area"] <= building_residential_max_area)  # m^2
    indexes_no = indexes & (poi_building["polygon_area"] > building_residential_max_area)  # m^2
    poi_building.loc[indexes_no, 'small_residential'] = 0
    poi_building.loc[indexes_no, 'large_residential'] = 0
    # poi_building.loc[indexes_yes, 'small_residential'] = 0.5
    # poi_building.loc[indexes_yes, 'large_residential'] = 0

    if city_center is not None:
        indexes_yes_yes = indexes_yes & poi_building.loc[indexes, "geometry"].within(
            city_center["geometry"].unary_union)  # inside city center
        indexes_yes_no = indexes_yes & ~(poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union))

        poi_building.loc[indexes_yes_no, 'small_residential'] = 0.5
        poi_building.loc[indexes_yes_no, 'large_residential'] = 0
        poi_building.loc[indexes_yes_yes, 'small_residential'] = 0
        poi_building.loc[indexes_yes_yes, 'large_residential'] = 0.5
    else:
        poi_building.loc[indexes_yes, 'small_residential'] = 0.5
        poi_building.loc[indexes_yes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # polygons priority == building in unlikely_residential_landuse (retail and commercial)
    indexes = (poi_building["landuse_outer"].apply(lambda x: any(lu in x for lu in ["retail", 'commercial']))) \
              & (poi_building['priority'] == 'building') \
              & (~indexes_loop)

    if city_center is not None:
        indexes_yes = indexes & poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union)  # inside city center
        indexes_no = indexes & ~(poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union))
        poi_building.loc[indexes_no, 'small_residential'] = 0
        poi_building.loc[indexes_no, 'large_residential'] = 0
        poi_building.loc[indexes_yes, 'small_residential'] = 0
        poi_building.loc[indexes_yes, 'large_residential'] = 0.8
    else:
        poi_building.loc[indexes, 'small_residential'] = 0
        poi_building.loc[indexes, 'large_residential'] = 0

    indexes_loop = indexes | indexes_loop

    # polygons priority == building in unlikely_residential_landuse (farmland, farmyard and forest)
    indexes = (poi_building["landuse_outer"].apply(lambda x: any(lu in x for lu in ["farmland", 'farmyard', 'forest']))) \
              & (poi_building['priority'] == 'building') \
              & (~indexes_loop)
    poi_building.loc[indexes, 'small_residential'] = 0.8
    poi_building.loc[indexes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # polygons priority == building and building != 'yes' + in residential landuse
    indexes = (poi_building["landuse_outer"].apply(lambda x: 'residential' in x)) \
              & (poi_building['priority'] == 'building') \
              & (~indexes_loop)

    tag_dic = {'building': ["yes"]}
    indexes = indexes & (~_indexes_tagged(poi_building, tag_dic))
    tag_dic = {'building:levels': ["1"]}
    indexes_no = indexes & (_indexes_tagged(poi_building, tag_dic))
    indexes_yes = indexes & (~indexes_no)
    poi_building.loc[indexes_no, 'small_residential'] = 0
    poi_building.loc[indexes_no, 'large_residential'] = 0
    poi_building.loc[indexes_yes, 'small_residential'] = 0.9
    poi_building.loc[indexes_yes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # polygons with only info: building = 'yes' and in residential landuse (10 000 polygons)
    indexes = (poi_building["landuse_outer"].apply(lambda x: 'residential' in x)) \
              & (poi_building['priority'] == 'building') \
              & (~indexes_loop)

    tag_dic = {'building': ["yes"]}
    indexes = indexes & (_indexes_tagged(poi_building, tag_dic))

    if city_center is not None:
        indexes_yes = indexes & poi_building.loc[indexes, "geometry"].within(
            city_center["geometry"].unary_union)  # inside city center
        indexes_no = indexes & ~(poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union))

        indexes_yes_no = indexes_yes & ~(poi_building[["building_inner_point", "amenity_inner_point", "leisure_inner_point",
                                                "sport_inner_point", "tourism_inner_point", "shop_inner_point",
                                                "office_inner_point", "amenity_inner_poly", "leisure_inner_poly",
                                                "sport_inner_poly", "tourism_inner_poly", "shop_inner_poly",
                                                "office_inner_poly"]].apply(
            lambda x: any(x.apply(lambda y: len(y) != 0)), axis=1))
        indexes_yes_yes = indexes_yes & ~indexes_yes_no

        indexes_no_no = indexes_no & ~(poi_building[["building_inner_point", "amenity_inner_point", "leisure_inner_point",
                                                       "sport_inner_point", "tourism_inner_point", "shop_inner_point",
                                                       "office_inner_point", "amenity_inner_poly", "leisure_inner_poly",
                                                       "sport_inner_poly", "tourism_inner_poly", "shop_inner_poly",
                                                       "office_inner_poly"]].apply(
            lambda x: any(x.apply(lambda y: len(y) != 0)), axis=1))
        indexes_no_yes = indexes_no & ~indexes_no_no

        poi_building.loc[indexes_yes_no, 'small_residential'] = 0
        poi_building.loc[indexes_yes_no, 'large_residential'] = 0.9
        poi_building.loc[indexes_yes_yes, 'small_residential'] = 0
        poi_building.loc[indexes_yes_yes, 'large_residential'] = 0.6
        poi_building.loc[indexes_no_no, 'small_residential'] = 0.9
        poi_building.loc[indexes_no_no, 'large_residential'] = 0
        poi_building.loc[indexes_no_yes, 'small_residential'] = 0.6
        poi_building.loc[indexes_no_yes, 'large_residential'] = 0
    else:
        indexes_no = indexes & ~(
        poi_building[["building_inner_point", "amenity_inner_point", "leisure_inner_point",
                      "sport_inner_point", "tourism_inner_point", "shop_inner_point",
                      "office_inner_point", "amenity_inner_poly", "leisure_inner_poly",
                      "sport_inner_poly", "tourism_inner_poly", "shop_inner_poly",
                      "office_inner_poly"]].apply(
            lambda x: any(x.apply(lambda y: len(y) != 0)), axis=1))
        indexes_yes = indexes & ~indexes_no

        poi_building.loc[indexes_no, 'small_residential'] = 0.9
        poi_building.loc[indexes_no, 'large_residential'] = 0
        poi_building.loc[indexes_yes, 'small_residential'] = 0.6
        poi_building.loc[indexes_yes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # building polygons outside any landuse polygon but an extra value (amenity, shop, or leisure_outer or ...) than building tag
    indexes = (poi_building["landuse_outer"].apply(lambda x: len(x) == 0)) & (~indexes_loop)
    indexes_no = indexes & ((poi_building['priority'] != 'building') | (poi_building[["building_inner_point", "amenity_inner_point", "leisure_inner_point",
                                                                                      "sport_inner_point", "tourism_inner_point", "shop_inner_point",
                                                                                      "office_inner_point", "amenity_inner_poly", "leisure_inner_poly",
                                                                                      "sport_inner_poly", "tourism_inner_poly", "shop_inner_poly",
                                                                                      "office_inner_poly"]].apply(lambda x: any(x.apply(lambda y: len(y) != 0)), axis=1)))

    # it means these building polygons have a value for leisure or amenity or shop or ...
    poi_building.loc[indexes_no, 'small_residential'] = 0
    poi_building.loc[indexes_no, 'large_residential'] = 0
    indexes_loop = indexes_no | indexes_loop

    # building polygons outside any landuse polygon and only a building tag
    indexes = (poi_building["landuse_outer"].apply(lambda x: len(x) == 0)) \
              & (~indexes_loop)
    indexes_no = indexes & (poi_building["building"] != 'yes')
    indexes_yes = indexes & (poi_building["building"] == 'yes')
    poi_building.loc[indexes_no, 'small_residential'] = 0
    poi_building.loc[indexes_no, 'large_residential'] = 0
    poi_building.loc[
        indexes_yes, 'small_residential'] = 0.1  # verfijnen nu veel gebouwen van op gasthuisberg bij en aan de vaart en de gevangenis vs de lintbebouwing die 1 polygon is, deze veel meer hoekjes kan dit helpen?
    poi_building.loc[indexes_yes, 'large_residential'] = 0
    indexes_loop = indexes | indexes_loop

    # go over every other polygon with customized rules
    indexes_loop = ~indexes_loop
    if indexes_loop.to_list().count(True) > 0:
        print(f"{indexes_loop.to_list().count(True)} polygons remained unclassified --> residential function = 0. "
              f"Look at the unconsidered tag list for more info.")
    else:
        print(f"All polygons were classified in terms of their residential function.")

    unconsidered_residential_tags = {}
    for col in poi_building.columns.to_list():
        if col not in essential_columns \
                and col not in extra_columns \
                and col not in activity_categories.keys() \
                and col not in ['small_residential', 'large_residential'] \
                and col not in ['priority', 'polygon_area']:
            if 'outer' in col or 'inner' in col:
                new_tags = poi_building.loc[
                    indexes & (poi_building[col].apply(lambda x: len(x) != 0)), col].value_counts()
            else:
                new_tags = poi_building.loc[indexes & (poi_building[col].notna()), col].value_counts()
            unconsidered_residential_tags[col] = new_tags

    poi_building = _update_to_area(poi_building, categories=["small_residential", "large_residential"])
    return poi_building, unconsidered_residential_tags


def _indexes_tagged(poi_building, tag_dic):
    indexes = np.full(len(poi_building), False)
    for key, values in tag_dic.items():
        if values == 'all':
            if 'outer' in key or 'inner' in key:
                indexes = indexes | poi_building[key].apply(lambda x: len(x) != 0)  # value not []
            else:
                indexes = indexes | poi_building[key].notna()
            continue
        for value in values:
            indexes = indexes | (poi_building[key] == value)

    return indexes


def categorise_activities(poi_building, poi_nonbuilding, city_center=None):
    # adds activity cateogries to polygons based on rules
    # value is in m²

    print("4. Categorizing activity buildings and areas.")

    # init categories
    poi_building['School'] = 0.0
    poi_building['Health'] = 0.0  # small and large
    poi_building['Leisure'] = 0.0  # indoor and outdoor, religious
    poi_building['Shops'] = 0.0  # food, other material
    poi_building['Services'] = 0.0  # public vs private
    poi_building['Industry'] = 0.0  # large vs small
    poi_building['Catering_industry'] = 0.0  # large vs small
    poi_building['Tourism'] = 0.0
    poi_building['Others'] = 0.0
    poi_building["Leisure_area"] = 0.0

    indexes_loop = np.full(len(poi_building), False)
    indexes = indexes_loop

    # clear activity function
    for cat in activity_categories.keys():
        if cat != 'Residential':
            tag_dic = activity_categories[cat]
            indexes_cat = _indexes_tagged(poi_building, tag_dic)
            for key in tag_dic.keys():
                if tag_dic[key] == "all":
                    if key != 'building':
                        indexes_cat = indexes_cat | poi_building[key + "_inner_poly"].apply(
                            lambda x: len(x) != 0)
                        indexes_cat = indexes_cat | poi_building[key + "_outer"].apply(
                            lambda x: len(x) != 0)
                    indexes_cat = indexes_cat | poi_building[key + "_inner_point"].apply(
                        lambda x: len(x) != 0)
                elif len(tag_dic[key]) != 0:
                    if key != 'building':
                        indexes_cat = indexes_cat | poi_building[key + "_inner_poly"].apply(
                            lambda x: any(value in x for value in tag_dic[key]))
                        indexes_cat = indexes_cat | poi_building[key + "_outer"].apply(
                            lambda x: any(value in x for value in tag_dic[key]))
                    indexes_cat = indexes_cat | poi_building[key + "_inner_point"].apply(
                        lambda x: any(value in x for value in tag_dic[key]))
            indexes_cat = indexes_cat & (~indexes_loop)
            indexes = indexes | indexes_cat
            poi_building.loc[indexes_cat, cat] = 1
            # eventueel gewicht op basis van hoeveel waarden er naar een bepaalde categorie verwijzen.
        elif cat == 'Residential':
            tag_dic = activity_categories[cat]
            indexes_cat = _indexes_tagged(poi_building, tag_dic)
            indexes_cat = indexes_cat & (~indexes_loop)
            indexes = indexes | indexes_cat
    indexes_loop = indexes | indexes_loop

    # Possible improvement: buildings with no own, inner or outer value in activity_categories lists but with attribute priority shop, amenity, leisure, ... classify as related activity?

    # catering_industry often combined with leisure or services, ... so then weight of catering industry should be put down
    indexes_catering = _indexes_tagged(poi_building, {"Catering_industry":[1]})
    indexes_combined = indexes_catering & _indexes_tagged(poi_building, {"Industry":[1], "Health":[1], "School":[1],
                                                                         "Leisure":[1], "Others":[1], "Tourism":[1]})
    poi_building.loc[indexes_combined, "Catering_industry"] = 0.1

    # less clear activity function: with no info in all the tags
    # buildings with only info building=yes and landuse_outer in landuse_based_activity_categories or not
    indexes = (~indexes_loop) & (poi_building["priority"] == "building") & (poi_building["building"] == "yes") & (
        poi_building[["amenity_outer", "leisure_outer", "sport_outer", "tourism_outer", "shop_outer", "office_outer"]].apply(
            lambda x: all(x.apply(lambda y: len(y) == 0)), axis=1))
    for cat in landuse_based_activity_categories.keys():
        if cat != "Residential":
            tag_dic = landuse_based_activity_categories[cat]
            indexes_cat = poi_building['landuse_outer'].apply(
                lambda x: any(value in x for value in tag_dic['landuse_outer']))
            indexes_cat = indexes_cat & (~indexes_loop)
            indexes_cat = indexes & indexes_cat
            poi_building.loc[indexes_cat, cat] = 1
        else:
            continue
            # these building_polygons will be listed as checked.
            # tag_dic = landuse_based_activity_categories[cat]
            # indexes_cat = poi_building['landuse_outer'].apply(
            #     lambda x: any(value in x for value in tag_dic['landuse_outer']))
            # indexes_cat = indexes_cat & (~indexes_loop)
            # indexes_cat = indexes & indexes_cat
    indexes_loop = indexes | indexes_loop

    # building with other value(s) than building yes but not in activity_categories and in landuse_outer: commercial, retail, industry, ...

    # buildings with other info not considered in activity_categories
    indexes = ~indexes_loop
    if indexes.to_list().count(True) > 0:
        print(f"{indexes.to_list().count(True)} polygons remained unclassified --> activity function = 0. "
              f"Look at the unconsidered tag list for more info.")
    unconsidered_activity_tags = {}
    for col in poi_building.columns.to_list():
        if col not in essential_columns \
                and col not in extra_columns \
                and col not in activity_categories.keys() \
                and col not in ['small_residential', 'large_residential'] \
                and col not in ['priority', 'polygon_area']:
            if 'outer' in col or 'inner' in col:
                new_tags = poi_building.loc[indexes & (poi_building[col].apply(lambda x: len(x) != 0)), col].value_counts()
            else:
                new_tags = poi_building.loc[indexes & (poi_building[col].notna()), col].value_counts()
            unconsidered_activity_tags[col] = new_tags

    # now buildings can be assigned to multiple categories: so scale down
    categories = list(activity_categories.keys())
    categories.remove('Residential')
    poi_building['temporary_sum_category_weights'] = poi_building[categories].sum(axis=1)
    for cat in categories:
        poi_building[cat] = poi_building[cat] / poi_building['temporary_sum_category_weights']
        poi_building[cat] = poi_building[cat].fillna(0) # if sum = 0 dividing by 0 = NaN
    poi_building = poi_building.drop(columns='temporary_sum_category_weights')

    indexes_services = _indexes_tagged(poi_building, {"Services": [1]})

    poi_building = _update_to_area(poi_building, categories=categories)

    if city_center is not None:
        indexes_yes = indexes_services & poi_building["geometry"].within(
            city_center["geometry"].unary_union)  # inside city center
        # indexes_no = indexes_services & ~(poi_building.loc[indexes, "geometry"].within(city_center["geometry"].unary_union))
        poi_building.loc[indexes_yes, 'Services'] = poi_building.loc[indexes_yes, 'Services'] * 2

    # non_building polygons that are used for leisure activity
    indexes = _indexes_tagged(poi_nonbuilding, non_building_activity_categories["Leisure"])
    poi_nonbuildingleisure = contains_polygon(poi_nonbuilding[indexes], mode="difference")

    poi_nonbuildingleisure['School'] = 0
    poi_nonbuildingleisure['Health'] = 0  # small and large
    poi_nonbuildingleisure['Leisure'] = 0  # indoor and outdoor, religious
    poi_nonbuildingleisure['Shops'] = 0  # food, other material
    poi_nonbuildingleisure['Services'] = 0  # public vs private
    poi_nonbuildingleisure['Industry'] = 0  # large vs small
    poi_nonbuildingleisure['Catering_industry'] = 0  # large vs small
    poi_nonbuildingleisure['Tourism'] = 0
    poi_nonbuildingleisure['Others'] = 0
    poi_nonbuildingleisure["Leisure_area"] = 0

    poi_nonbuildingleisure.loc[indexes, "Leisure_area"] = 1
    poi_nonbuildingleisure = _update_to_area(poi_nonbuildingleisure, categories=["Leisure_area"])

    poi_building_categorized = poi_building[poi_building[categories + ['small_residential', 'large_residential']
                                                         ].apply(lambda x: any(x.apply(lambda y: y > 0)), axis=1)]
    poi_nonbuildingleisure_categorized = poi_nonbuildingleisure[poi_nonbuildingleisure["Leisure_area"] > 0]

    # for now points that are not inside a building are not included in categorization
    return poi_building_categorized, poi_nonbuildingleisure_categorized, unconsidered_activity_tags


def _update_to_area(poi_building, categories):
    for cat in categories:
        poi_building[cat] = poi_building[cat] * poi_building['polygon_area']
    return poi_building
