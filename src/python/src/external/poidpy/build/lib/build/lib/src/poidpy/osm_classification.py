# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Jeroen Verstraete, Lotte Notelaers
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

# This file contains all default parameters for downloading, selecting, cleaning and categorizing OSM data into POIs types.

# Download parameters
tags_default = {'landuse': True, 'building': True, 'amenity': True, 'leisure': True,
                'shop': True, 'office': True, 'sport': True, 'tourism': True}

# Parameters for variable selection
attribute_columns = list(tags_default.keys())
essential_columns = ['osmid', 'geometry']
extra_columns = ['building:levels', 'addr:housenumber']
data_columns_default = []
data_columns_default.extend(essential_columns)
data_columns_default.extend(attribute_columns)
data_columns_default.extend(extra_columns)

default_ignore_tags = {"landuse": ["flowerbed", "grass", "meadow", "urban_green", "village_green", "green_field", "brownfield"],
                       "amenity": ["toilets", "bench", "waste_basket", "post_box", "waste_disposal", "bicycle_parking",
                                   "bus_station", "car_sharing", "car_pooling", "charging_station", "fountain", "motorcycle_parking",
                                   "parking", "parking_entrance", "parking_space", "shelter", "smoking_area", "trolley_bay",
                                   "parking_exit", "vending_machine", "compressed_air", "drinking_water", "hunting_stand",
                                   "clock", "parcel_locker", "public_bookcase", "taxi", "water_point", "vacuum_cleaner",
                                   "payment_terminal", "letter_box", "watering_place", "luggage_locker", "photo_booth",
                                   'tourist_bus_parking', 'bicycle_repair_station', 'coast_radar_station', 'reception_desk',
                                   'device_charging_station', 'disused', 'dog_toilet', 'dressing_room', 'shower',
                                   'water_point', 'weighbridge'],
                       "leisure": ["outdoor_seating", "village_green", "schoolyard", "bleachers", "firepit", "bird_hide",
                                   "picnic_table", "fitness_station", "slipway"],
                       "building": ["barn", "bridge", "bunker", "cabin", "carport", "cowshed", "garage", "garages",
                                    "gatehouse", "guardhouse", "grandstand", "greenhouse", "porch", "roof", "shed", "stable", "toilets",
                                    "transformer_tower", "planned", "proposed", "pavilion", "parking", "slurry_tank", "tent", 'water_tower'],
                       "sport": ["table_tennis"]}

# Parameters for cleaning OSM data
building_threshold_area = 40 # buildings below 40 square meter will not generate trips on their own but will be part of another dominant building e.g. garden shed accompanied by a house
tag_priority_default = ('shop', 'office', 'leisure', 'sport', 'tourism', 'amenity', 'building', 'landuse')

# Parameters for categorizing OSM data
building_residential_max_area = 600 # buildings above 600 m^2 are very unlikely to be residential buildings (although apartments buildings are sometimes bigger)

# based on OSMtaglist API for Belgium:
activity_categories = {"Residential": {'building': ['allotment_house', 'apartments', 'bungalow', 'detached', 'dormitory',
                                                    'farm', 'farm_auxiliary', 'house', 'houseboat', 'semidetached_house',
                                                    'static_caravan', 'stilt_house', 'terrace', 'residential', 'home'],  # building = hut ignore, residential or recreation?
                                       'amenity': [],
                                       'office': [],
                                       'shop': [],
                                       'leisure': [],
                                       'tourism': [],
                                       'sport': []},
                       "School": {'building': ['college', 'kindergarten', 'school', 'university', 'conservatory'],
                                  'amenity': ['college', 'kindergarten', 'language_school', 'prep_school', 'school', 'university',
                                              'childcare', 'research_institute'],
                                  'office': ['educational_institution', 'research'],
                                  'shop': [],
                                  'leisure': [],
                                  'tourism': [],
                                  'sport': []},
                       "Health": {'building': ['hospital'],
                                  'amenity': ['clinic', 'dentist', 'hospital', 'nursing_home', 'pharmacy', 'retirement_home',
                                              'social_facility', 'doctors', 'nursery'],
                                  'office': ['therapist'],
                                  'shop': [],
                                  'leisure': [],
                                  'tourism': [],
                                  'sport': []},
                       "Leisure": {'building': ['marquee', 'sports_centre', 'sports_hall', 'stadium', 'museum', 'ruins'],
                                   'amenity': ['arts_centre', 'diving_centre', 'events_venue', 'music_venue',
                                               'ski_school', 'social_centre', 'theatre', 'yacht_club',
                                               'events_venue', 'dive_centre', 'dancing_school',
                                               'music_school', 'planetarium', 'gym', 'gambling', 'animal_training', 'dojo'],
                                   'office': [],
                                   'shop': [],
                                   'leisure': ['adult_gaming_centre', 'amusement_arcade', 'bandstand',
                                               'bowling_alley', 'common', 'dance', 'disc_golf_course', 'dog_park',
                                               'escape_game', 'fishing', 'fitness_centre', 'fitness_station', 'golf_course',
                                               'hackerspace', 'horse_riding', 'ice_rink', 'marina', 'maze', 'miniature_golf',
                                               'nature_reserve', 'park', 'pitch', 'playground', 'recreation_ground', 'resort',
                                               'sauna', 'sports_centre', 'sports_hall', 'stadium', 'summer_camp',
                                               'tanning_salon', 'track', 'indoor_play'],
                                   'tourism': ['trail_riding_station'],
                                   'sport': 'all'},
                       "Services": {'building': ['civic', 'government', 'public', 'service', 'office', 'transportation', 'commercial', 'conference_centre'],
                                    'amenity': ['atm', 'bank', 'post_office', 'co_working_space', 'courthouse', 'driver_training',
                                                'fire_station', 'library', 'archive', 'public_building', 'refugee_housing',
                                                'driving_school', 'police', 'prison', 'community_centre', 'veterinary',
                                                'mortuary', 'crematorium', 'animal_shelter', 'mortuar', 'audiologist',
                                                'baby_hatch', 'bureau_de_change', 'car_rental', 'car_wash', 'financial_advice',
                                                'money_transfer', 'payment_centre', 'studio', 'conference_centre',
                                                'car_wash', 'fuel', 'fuel - petrol', 'fuel - petroleum', 'dry_cleaning',
                                                'dry_cleaning - laundry', 'laundry', 'townhall' ,'exhibition_centre', 'events_centre'
                                                ],
                                    'office': ['yes', 'advertising_agency', 'graphic_design', 'insurance', 'it', 'law_firm',
                                               'newspaper', 'tax_advisor', 'property_management', 'administrative',
                                               'association', 'charity', 'company', 'consulting', 'diplomatic', 'foundation',
                                               'government', 'law_firm', 'accountant', 'architect', 'co_working', 'ngo',
                                               'notary', 'political_party', 'quango', 'surveyor', 'non-profit', 'lawyer',
                                               'translation', 'telecommunication', 'employment_agency', 'estate_agent',
                                               'travel_agent', 'health_insurance', 'construction_company', 'publisher'],
                                    'shop': ['funeral_directors', 'estate_agent', 'mutualiteit', 'fuel', 'hairdresser',
                                             'massage', 'ironingshop', 'laundry', 'charity', 'travel_agency'],
                                    'leisure': [],
                                    'tourism': [],
                                    'sport': []},
                       # public vs private services?
                       "Shops": {'building': ['kiosk', 'retail', 'supermarket', 'commercial'],
                                 'amenity': ['shop', 'supermarket',
                                             'bicycle_rental', 'brothel', 'marketplace', 'animal_boarding', 'animal_breeding',
                                             'ice_cream'],
                                 'office': [],
                                 'shop': ['yes', 'curtains', 'curtain', 'baby', 'bike_repair', 'doityourself', 'doors', 'fireplace', 'flooring', 'furniture',
                                          'household_linen', 'houseware', 'interior_decoration', 'kitchen', 'kitchenware',
                                          'lighting', 'locks', 'painting', 'security', 'window_blind', 'windows', 'books',
                                          'medical_supply', 'games', 'hobby', 'music', 'musical_instrument', 'sports',
                                          'swimming_pool', 'toys', 'video', 'video_games', 'accessories', 'anime', 'antiques',
                                          'appliance', 'baby_goods', 'bag', 'bathroom_furnishing', 'beauty', 'bed', 'beverages',
                                          'bicycle', 'bookmaker', 'boutique', 'brewing_supplies', 'butcher', 'camera', 'candles',
                                          'cannabis', 'car_parts', 'car_repair', 'car_service', 'caravan', 'carpet', 'cheese',
                                          'chemist', 'chocolate', 'clothes', 'coffee', 'collector', 'computer', 'confectionery',
                                          'convenience', 'copyshop', 'cosmetics', 'country_store', 'craft', 'dairy', 'deli',
                                          'department_store', 'doors', 'dry_cleaning', 'e-cigarette', 'electrical', 'electronics',
                                          'equestrian', 'erotic', 'fabric', 'fashion', 'fashion_accessories',
                                          'fireworks', 'fish', 'fishing', 'florist', 'frame', 'frozen_food', 'furnace',
                                          'furniture', 'games', 'garden_centre', 'garden_furniture', 'gas', 'general', 'gift',
                                          'glaziery', 'golf', 'greengrocer', 'grocery', 'groundskeeping', 'haberdashery',
                                          'hairdresser_supply', 'hardware', 'health_food', 'hearing_aids', 'herbalist', 'hifi',
                                          'hobby', 'hookah', 'household', 'household_linen', 'houseware', 'hunting', 'jewelry',
                                          'kiosk', 'kitchen', 'kitchenware', 'leather', 'locksmith', 'mall',
                                          'mobile_home', 'mobile_phone', 'model', 'money_lender', 'motorcycle',
                                          'motorcycle_repair', 'motorhome', 'music', 'musical_instrument', 'newsagent',
                                          'nutrition_supplements', 'nuts', 'office_supplies', 'optician', 'outdoor', 'outpost',
                                          'paint', 'party', 'pawnbroker', 'perfumery', 'pest_control', 'pet', 'pet_grooming',
                                          'photo', 'photography', 'pottery', 'printer_ink', 'printing', 'pyrotechnics',
                                          'radiotechnics', 'sewing', 'ship_chandler', 'shoe_repair', 'shoes', 'ski', 'souvenir',
                                          'spare_parts', 'spices', 'sports', 'stationery', 'supermarket', 'swimming_pool',
                                          'tailor', 'tattoo', 'tea', 'ticket', 'tiles', 'tobacco', 'tool_hire', 'toys', 'trade',
                                          'trailer', 'trophy', 'tyres', 'vacuum_cleaner', 'variety_store', 'video', 'video_games',
                                          'watches', 'weapons', 'wholesale', 'wigs', 'window_blind', 'windows', 'wine', 'wool',
                                          'stairs', 'electronic_games', 'second_hand', 'seafood', 'alcohol',
                                          'gps_and_communication', 'icecream', 'bakery', 'food', 'pastry', 'car',
                                          'scuba_diving', 'art', 'huisraad', 'telecommunication'],
                                 'leisure': ['tanning_salon'],
                                 'tourism': [],
                                 'sport': []},
                       "Catering_industry": {'building': ['restaurant'],
                                             'amenity': ['bar', 'biergarten', 'cafe', 'fast_food', 'food_court', 'hookah_lounge',
                                                         'karaoke_box', 'restaurant', 'snack_bar', 'internet_cafe',
                                                         'canteen', 'stripclub', 'nightclub', 'swingerclub', 'pub'],
                                             'office': [],
                                             'shop': ['cafe'],
                                             'leisure': ['club', 'social_club'],
                                             'tourism': [],
                                             'sport': []},
                       "Industry": {'building': ['bakehouse', 'brewery', 'construction', 'container', 'digester', 'industrial',
                                                 'manufacture', 'riding_hall', 'warehouse', 'hangar', 'data_center', 'tech_cab'],
                                    'amenity': ['boat_storage', 'car_rental', 'post_depot', 'recycling', 'vehicle_inspection',
                                                'waste_transfer_station', 'motorhome - cleaning'
                                                ],
                                    'office': ['forestry', 'moving_company', 'energy_supplier', 'water_utility', 'engineer',
                                               'geodesist', 'logistics',
                                               ],
                                    'shop': ['farm', 'military_surplus', 'storage_rental'],
                                    'leisure': [],
                                    'tourism': [],
                                    'sport': []
                                    },
                       "Others": {'building': ['cathedral', 'chapel', 'church', 'mosque', 'shrine', 'basilica', 'temple', 'synagogue','cloister', 'monastery'],
                                  'amenity': ['place_of_worship', 'monastery', "grave_yard", 'crypt'],
                                  'office': ['parish'
                                             ],
                                  'shop': [],
                                  'leisure': [],
                                  'tourism': [],
                                  'sport': []
                                  },
                       "Tourism": {"building": ['stadium', 'museum', 'love_hotel', 'hotel'],
                                   "amenity": ['trampoline_park', 'water_park', 'boat_rental', 'casino', 'cinema', 'concert_hall'],
                                   "leisure": ['beach_resort', 'marina', 'swimming_area', 'swimming_pool'],
                                   "tourism": ['alpine_hut', 'aquarium', 'artwork', 'attraction', 'camp_site', 'caravan_site',
                                               'chalet', 'gallery', 'guest_house', 'hostel', 'hotel', 'information', 'motel',
                                               'museum', 'resort', 'theme_park', 'viewpoint', 'zoo']}
                       }

landuse_based_activity_categories = {"School": {'landuse_outer': ['education']},
                                     "Leisure": {'landuse_outer': ['recreation_ground']},
                                     "Services": {'landuse_outer': ['commercial']},
                                     "Shops": {'landuse_outer': ['retail']},
                                     "Catering_industry": {'landuse_outer': []},
                                     "Industry": {'landuse_outer': ['industrial', 'railway', 'military', 'depot',
                                                                    'landfill']},
                                     "Others": {'landuse_outer': ['construction', 'cementery']},
                                     "Residential": {'landuse_outer': ['residential']}
                                     }

non_building_activity_categories = {"Leisure": {  # "landuse": ["recreation_ground"], often just green area in city
    "leisure": ["pitch", "playground", "park", "dog_park", "track",
                "sports_centre", "stadium", "fishing", "skate", "marina",
                "recreation_ground", "miniature_golf"],
    "sport": "all"}}
