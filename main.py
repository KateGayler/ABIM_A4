# -*- coding: utf-8 -*-
"""
Created on Mon Sep 25 14:53:25 2023

@author:
"""
#Import libraries
from pathlib import Path
import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
import ifcopenshell.util.shape
import ifcopenshell.util.unit
import ifcopenshell.geom
import uuid
import numpy as np
import matplotlib.pyplot as plt 
import pandas as pd

#Import model by canging the model name. 
#Make sure that model is placed in right folder
modelname = "LLYN - ARK_Qto"

try:
    dir_path = Path(__file__).parent
    model_url = Path.joinpath(dir_path, 'model', modelname).with_suffix('.ifc')
    model = ifcopenshell.open(model_url)
except OSError:
    try:
        import bpy
        model_url = Path.joinpath(Path(bpy.context.space_data.text.filepath).parent, 'model', modelname).with_suffix('.ifc')
        model = ifcopenshell.open(model_url)
        
    except OSError:
        print(f"ERROR: please check your model folder : {model_url} does not exist")
        
        
########################## Format check #################################

#Checks the IFC format of the file - Should be IFC4
format = model.schema
if format == "IFC4":
    print(f"\n The file format is {format} and is okay")
else:
    print(f"\n The file is {format} and not IFC4. The model should therefore be updated to IFC4.")

########################## Space data ##########################
#Store all spaces
spaces = model.by_type("IfcSpace")

#Determine dumber of spaces
spaces_in_model = len(spaces)
print(f"\n There are {spaces_in_model} spaces in the model.")


########################## Adding quantities ####################
#Areas are calculated based on: https://github.com/IfcOpenShell/IfcOpenShell/blob/f0502c123ea61c5574a7cb0d8e293afc94c4ec1e/src/blenderbim/blenderbim/bim/module/pset/qto_calculator.py#L210
#Retrieved: 31/10/2023

#Settings of the geometry
unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
settings = ifcopenshell.geom.settings()

#For-loop that calculates the net floor area and net volume of a space 
#Which is then assigned to QtoSpaceBaseQuantities if. 
#If missing parts for this quantitiy set, they're created (cheks for this)
for space in spaces:
    net_shape = ifcopenshell.geom.create_shape(settings, space)
   
   # Calculates netarea and -volume for the space
   
   # length = ifcopenshell.util.shape.get_x(net_shape.geometry) / unit_scale
   # width = ifcopenshell.util.shape.get_y(net_shape.geometry) / unit_scale
   # height = ifcopenshell.util.shape.get_z(net_shape.geometry) / unit_scale
    net_area = round(ifcopenshell.util.shape.get_footprint_area(net_shape.geometry),2)
    net_volume = round(ifcopenshell.util.shape.get_volume(net_shape.geometry),2)
    
    Defines = space.IsDefinedBy
    
    #Definies flag used to indicated if the wanted quantity set is defined
    flag = False
    
    #Retrieves quantities of the space
    qsets_space = ifcopenshell.util.element.get_psets(space,qtos_only=True)
    if "Qto_SpaceBaseQuantities" in qsets_space:
        flag = True
        for definition in Defines:
            x=definition.RelatingPropertyDefinition
            if x.is_a('IfcElementQuantity'):
                if x.Name == 'Qto_SpaceBaseQuantities':
                  Quant = x.Quantities
                  if Quant is None: 
                      #Creates IfcQuantitiyArea and IfcQuantityVolume
                      print(f"Assigning IfcQuantitiyArea and IfcQuantityVolume to Qto_SpaceBaseQuantities for {space.LongName}")
                      ent_area=model.create_entity('IfcQuantityArea')
                      ent_volume=model.create_entity('IfcQuantityVolume')
                      ent_area.Name="NetFloorArea"
                      ent_volume.Name="NetVolume"
                      Quant=(ent_area,ent_volume)
                      x.Quantities=Quant
                  print(f"For {space.LongName} a floor area of {net_area} and a volume of {net_volume} is assigned to the model")
                  #Assigns values to the quantity set
                  for hit in Quant: 
                      if hit.is_a("IfcQuantityArea") and hit.Name == "NetFloorArea":
                          hit.AreaValue =net_area
                      if hit.is_a("IfcQuantityVolume") and hit.Name == "NetVolume":
                          hit.VolumeValue = net_volume
    
    #If the quantity set is not defined, a new one is made, with values 
    if not flag:
        print(f"Creating quantity set for {space.LongName} with floor area of {net_area} and volume of {net_volume}")
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid1().hex)
        owner_history = model.by_type("IfcOwnerHistory")[0]

        area_values = model.createIfcQuantityArea("NetFloorArea",None,None, net_area,None)                                        
        volume_values = model.createIfcQuantityVolume("NetVolume",None,None, net_volume,None)
        quantity_set = model.createIfcElementQuantity(create_guid(), owner_history, 'Qto_SpaceBaseQuantities', None,None, (area_values,volume_values))
        model.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [space], quantity_set)
      
##Creates a loop, that loops through all the rooms and retrieves the data
#Empty variables are made to append data to
floor_covering = []
space_volume=[]
space_area=[]
space_ceiling_area=[]
space_LongName=[]
space_Name=[]
i = 0

#Retrieves the needed property+quantity of a space. If the needed property sets are not available,
# 0 is appended
#Retrieves: Space volume, area, and floor covering
for space in spaces:
    psets_space = ifcopenshell.util.element.get_psets(space,psets_only=False)
    space_LongName.append(space.LongName)
    space_Name.append(space.Name)
    if "Qto_SpaceBaseQuantities" in psets_space and "NetVolume" in psets_space["Qto_SpaceBaseQuantities"]:
        space_volume.append(psets_space["Qto_SpaceBaseQuantities"]["NetVolume"])
        space_area.append(psets_space["Qto_SpaceBaseQuantities"]["NetFloorArea"])
        i = i+1
    else: 
        space_volume.append(0)
        space_area.append(0)
       # space_ceiling_area.append(0)
    if "Pset_SpaceCoveringRequirements" in psets_space:
        floor_covering.append(psets_space["Pset_SpaceCoveringRequirements"]["FloorCovering"])
    else: 
        floor_covering.append("0")

#Overview of the number of rooms with quantities
if i == spaces_in_model:
    print("\n All spaces in the model contain the necessary quantities.\n")
else: 
    print(f"\n {i} spaces contain quantities out of {spaces_in_model} spaces. You may want to add quantities to the remaining spaces.\n")

#Merges the space number together with the longname of the space
space_description = [x + ' ' + y for x, y in zip(space_Name, space_LongName)]

########################## Wall data ##################################  
#Empty variables
wall_space_total = []
matrix_wall_area = []
matrix_wall_material=[]

#Creates a loop that goes through all the spaces, identifies the boundering elements
#And for the ones that are wall, find the wall material and wall area
#The wall material and area is stored in a matrix, so each wall of a room can be 
#identified with the corresponding material, since not all walls of a room has the same material
for space in spaces:
    near = space.BoundedBy
    wall_space_area = []
    wall_material = []
    for objects in near:
        if (objects.RelatedBuildingElement != None):
            if (objects.RelatedBuildingElement.is_a('IfcWall')):
                material = ifcopenshell.util.element.get_material(objects.RelatedBuildingElement)
                if material.is_a("IfcMaterial"):
                    wall_material.append(material.Name)
                if material.is_a("IfcMaterialConstituentSet"):
                    Constituent=material.MaterialConstituents[-1]   #Assumes that the material closest to the room is defined last
                    Constituent_material = Constituent.Material
                    wall_material.append(Constituent_material.Name)
                psets_wall = ifcopenshell.util.element.get_psets(objects.RelatedBuildingElement)
                if "Qto_WallBaseQuantities" in psets_wall:
                    wall_space_area.append(psets_wall["Qto_WallBaseQuantities"]["NetSideArea"])
    matrix_wall_material.append(wall_material)
    matrix_wall_area.append(wall_space_area)
    wall_space_total.append(np.sum(wall_space_area))


############################### Calculation of VOC concentration #############################
 
#Define SER values (off-gassing values) for known materials
materials = {"Epoxy":25,"Beton":5,"Vinyl":30,"Fliser":0,"Gummi":15}     #ug/h/m2

#Function that search for partial matches between dictionary key and searchword
def partial_match(search_word, keys):
    for key in keys:
        if key in search_word:
            return key
    return None

#Makes a list of SER values corresponding to each floor covering in each space
floor_SER = [materials[partial_match(word, materials.keys())] if partial_match(word, materials.keys()) is not None else 0 for word in floor_covering]

#Calculates the emission rate. The space area equals the floor covering area
emission_rate_floor = np.multiply(floor_SER,space_area)       #ug/h

#Defining the ventilation rate to be 0,7 l/s*m2 (since unknown in model) and calculates air change rate of the space
ventilation_rate = [0.7 for _ in range(len(space_area))]    #l/s*m2
air_change = np.divide((np.multiply(ventilation_rate,space_area)*(10**(-3))*3600),space_volume)     #h^-1

#Calculation of VOC concentration and relating VOC concentration to room in a dictionary
VOC_concentration = np.around(np.divide(emission_rate_floor,np.multiply(air_change,space_volume)),3)             #ug/m3
zip_dict = dict(zip(space_description,VOC_concentration))


########################### Data visualisation #################################

#Create a dataframe df for easier management of all of the data
data = {"Space number":space_Name,"Space type":space_LongName,"Floor area":space_area,
        "Room volume":space_volume,"Floor covering":floor_covering,"VOC concentration":VOC_concentration}
df = pd.DataFrame(data)

#Exports dataframe to an excel file with a given path
dataframe_out_url = Path.joinpath(dir_path, 'output', "Dataframe").with_suffix('.xlsx')
df.to_excel(dataframe_out_url, sheet_name='Sheet1')

print(f"\n The VOC for each room is now calculated. The data for each room can be found in the dataframe df or as an excel file in the 'Output' folder. \n \n {df}")

#Plot of the concentrations in the rooms
indices = np.where(~np.isnan(VOC_concentration))[0]     #Gets all the indices where there are calculated VOC concentration

plt.figure(figsize=(20, 5))
plt.bar(np.array(space_description)[indices], np.array(VOC_concentration)[indices], color ='maroon', width = 0.4)    

plt.xticks(fontsize = 8,rotation=90)
plt.title("VOC concentration pr. room")
plt.xlabel("Room name")
plt.ylabel("VOC concentration [ug/m3]")
 
print("\n The VOC concentration is plotted as bar plots in the 'plots' tab.")

#Finds the 'Top 10 worst rooms' in the building
indices10 = np.argsort(np.array(VOC_concentration)[indices])[-10:]
top10_VOC = [np.array(VOC_concentration)[indices][i] for i in indices10]
top10_spaces = [np.array(space_description)[indices][i] for i in indices10]

print(f"\n The 10 worst spaces in the model are:{top10_spaces}, with the given values:\n")

for top10_spaces, top10_VOC in zip(top10_spaces, top10_VOC):
    print(f"{top10_spaces:<15}{top10_VOC}\n")

############# Creates new pset for VOC concentration ################
#Creates necesary data for new property set
create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid1().hex)
owner_history = model.by_type("IfcOwnerHistory")[0]

#Loops through all spaces and creates new property set for VOC off-gassing values
for index, row in df.iterrows():
    print(f"adding voc for row {index}, value {row['VOC concentration']}")
    property_values = [model.createIfcPropertySingleValue("VOC_Conc","VOC_Conc", model.create_entity("IfcReal", row['VOC concentration']),None)]                                        
    property_set = model.createIfcPropertySet(create_guid(), owner_history, "Pset_VOCConc", None, property_values)
    model.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [spaces[index]], property_set)

###################### Change of floor covering #####################
#Creates a user interface where it's possible to swap out the floor covering of a room

#Possible floor coverings to change to
valid_covering_types = [
    "Epoxy",
    "Vinyl",
    "Laminate",
    "Hardwood",
    "Bamboo",
    "Stone Tile",
]

#Function to retrieve floor covering
def get_floor_covering(space):
    for property_set in space.IsDefinedBy:
        if (
            hasattr(property_set, "RelatingPropertyDefinition")
            and property_set.RelatingPropertyDefinition.is_a("IfcPropertySet")
            and property_set.RelatingPropertyDefinition.Name
            == "Pset_SpaceCoveringRequirements"
        ):
            properties = property_set.RelatingPropertyDefinition.HasProperties
            for prop in properties:
                if prop.Name == "FloorCovering":
                    return prop.NominalValue.wrappedValue
    return False


spaces = [space for space in model.by_type("IfcSpace") if get_floor_covering(space)]

#Creates a list of the current floor coverings
def list_floor_coverings():
    print("Current floor coverings:")
    for space in spaces:
        current_covering = get_floor_covering(space)
        print(
            f"Space number: {space[2]}, type: {space[7]}, floor covering: {current_covering}"
        )

#Creates a function to change the floor covering
def change_floor_coverings():
    print("Select a space:")
    for i, space in enumerate(spaces, 1):
        print(f"{i}) {space[2]}: {space[7]}")

    try:
        selection = int(
            input("\nEnter the number corresponding to the space you want to change: ")
        )
        space = spaces[selection - 1]
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a valid number.")
        return

    property_sets = model.by_type("IfcRelDefinesByProperties")

    property_sets = space.IsDefinedBy

    for property_set in property_sets:
        if (
            hasattr(property_set, "RelatingPropertyDefinition")
            and property_set.RelatingPropertyDefinition.is_a("IfcPropertySet")
            and property_set.RelatingPropertyDefinition.Name
            == "Pset_SpaceCoveringRequirements"
        ):
            properties = property_set.RelatingPropertyDefinition.HasProperties

            for prop in properties:
                if prop.Name == "FloorCovering":
                    floor_covering_value = prop.NominalValue.wrappedValue
                    print(
                        f"Updating floor Covering for space {space[2]} with current covering: {floor_covering_value}"
                    )
                    for i, covering_type in enumerate(valid_covering_types, 1):
                        print(f"{i}) {covering_type}")
                    try:
                        selection = int(input("\n\nSelect new floor covering type: "))
                        new_covering = valid_covering_types[selection - 1]
                        prop.NominalValue = model.createIfcText(new_covering)

                    except (ValueError, IndexError):
                        print("Invalid selection. Please enter a valid number.")
                        return
    print("Floor covering updated.")

# Path for output file
model_out_url = Path.joinpath(dir_path, 'output', modelname + "_out").with_suffix('.ifc')

# Main interaction loop
while True:
    selected = input(
        "\nPlease select one of the following options\n\t1) Show current floor covering.\n\t2) Change floor covering.\n\t3) Save model and exit\nOption: "
    )
    if selected == "1":
        list_floor_coverings()
    elif selected == "2":
        change_floor_coverings()
    elif selected == "3":
        # Save file and exit
        model.write(model_out_url)
        break
    else:
        print("\nplease select either 1, 2, 3.")

# sanity check - is the new property and quantitity sets being written to the output file?
try:
    dir_path = Path(__file__).parent
    model_url = Path.joinpath(dir_path, 'output', modelname + "_out").with_suffix('.ifc')
    model = ifcopenshell.open(model_url)
except OSError:
    try:
        import bpy
        model_url = Path.joinpath(Path(bpy.context.space_data.text.filepath).parent, 'model', modelname).with_suffix('.ifc')
        model = ifcopenshell.open(model_url)
        
    except OSError:
        print(f"ERROR: please check your model folder : {model_url} does not exist")

#Prints property and quantitity set of all the spaces. Remove # for print
spaces = model.by_type("IfcSpace")
for space in spaces:
    psets_space = ifcopenshell.util.element.get_psets(space,psets_only=False)
    #print(psets_space)