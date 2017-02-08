bl_info = {
    "name": "Molecule Generator",
    "description": "Generates 3D molecules from .sdf format files.",
    "author": "Andrew Snelling",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "View3D > Add > Mesh",
    "warning": "",
    "wiki_url": "N/A",
    "tracker_url": "N/A",
    "support": "TESTING",
    "category": "Add Mesh"
    }

import bpy, os, math

# A dictionary used to look up the van der Waals radii of atoms. The values are measured in angstroms.
RADII = {'H':1.2, 'He':1.4, 'Li':1.82, 'C':1.7, 'N':1.55, 'O':1.52, 'F':1.47,
'Ne':1.54, 'Na':2.27, 'Mg':1.73, 'Si':2.1, 'P':1.8, 'S':1.8, 'Cl':1.75, 'Ar':1.88}

# A dictionary used to look up the colour that atoms are to be represented in.
COLOR = {'H':(1,1,1), 'He':(0,1,1), 'Li':(0.184,0,1), 'C':(0.016,0.016,0.016),
'N':(0.016,0.033,1), 'O':(1,0.016,0), 'F':(0.014,0.871,0.014), 'Ne':(0,1,1),
'Na':(0.184,0,1), 'Mg':(0,0.184,0), 'Si':(0.723,0.184,1), 'P':(1,0.319,0),
'S':(0.723,0.723,0), 'Cl':(0.014,0.871,0.014), 'Ar':(0,1,1)}

class MolGen(bpy.types.Operator):
    """Molecule Generator"""
    bl_idname = "object.mol_gen"
    bl_label = "Generate Molecule"
    bl_options = {'REGISTER', 'UNDO'}
    
    # This list will store atoms in tuples in the format of (x, y , z, symbol).
    atoms = []
    
    # User defined scale factor for atoms. Scale of 1 will give a space-filling model.
    atomScale = bpy.props.FloatProperty(name = "Atom scale factor", default = 0.25)
    # If the user checks the "Hide bonds" option, no bonds will be created.
    hideBonds = bpy.props.BoolProperty(name = "Hide bonds")
    # "Bond radius" allows the user to make bonds wider or thinner.
    bondRadius = bpy.props.FloatProperty(name = "Bond radius", default = 0.05)
    # If the "Hide Hydrogen" option is checked, no hydrogen atoms or bonds connecting to hydrogen atoms will be made.
    hideHydrogen = bpy.props.BoolProperty(name = "Hide hydrogen")
    # If the "Minimal carbon" is checked option, carbon atoms will be generated with the same radius as their bonds.
    minimalCarbon = bpy.props.BoolProperty(name = "Minimal carbon")
    # The file given must be written in .sdf format, but it does not have to have the .sdf file extension.
    filepath = bpy.props.StringProperty(name = "Molecule file", subtype = "FILE_PATH")
                                        
    def addAtom(self, symbol, x, y, z):     # Adds an atom with the given symbol at coordinates x,y,z.       
        if self.hideHydrogen and symbol == "H": return

        if self.minimalCarbon and symbol == "C":
            bpy.ops.mesh.primitive_ico_sphere_add(size = self.bondRadius,
            subdivisions = 4, location = (x, y, z))
        else:
            bpy.ops.mesh.primitive_ico_sphere_add(size = RADII[symbol]*self.atomScale,
            subdivisions = 4, location = (x, y, z))
        # Atom now exists, but without a material.
        
        if (bpy.data.materials.get("element_"+symbol) is None):
            # If the appropriate material has not yet been created, create it.
            mat = bpy.data.materials.new("element_"+symbol)
            mat.diffuse_color = COLOR[symbol]
        # Apply the appropriate material.
        bpy.context.object.data.materials.append(bpy.data.materials.get("element_"+symbol))
        # Not strictly neccesary, but smooth shading looks better in this case.
        bpy.ops.object.shade_smooth()
    
    def addBond(self, a1, a2, n):
        # Creates n bonds between the atom with index number a1 and that with index number a2.
        # Don't create any bonds if hideBonds is true.
        if self.hideBonds: return
        # Don't create any bonds if hideHydrogen is true and one or both of the atoms are hydrogen.
        if self.hideHydrogen and (self.atoms[a1][3] == "H" or self.atoms[a2][3] == "H"): return
        
        # Finding the delta x, y, and z values of the atoms' positions.
        dX = self.atoms[a2][0]-self.atoms[a1][0]
        dY = self.atoms[a2][1]-self.atoms[a1][1]
        dZ = self.atoms[a2][2]-self.atoms[a1][2]
        
        # Finding the x and y rotations of the bond.
        if dX == 0 and dZ == 0:
            rotX = math.pi/2
        else:
            rotX = math.atan(dY/math.sqrt(dZ**2+dX**2))
        if dZ == 0:
            rotY = math.pi/2
        else:
            rotY = math.atan(dX/dZ)
        if 0<dZ: rotX = -rotX
        
        for i in range(n):
            # Makes each individual bond.
            # Multiple bonds between the same atoms are displaced along the x and y axes, but not the z axis.
            # This ensures that the number of bonds is clearly visible when looking down from above or up from below.
            
            # Finds the straightline distance between the two atoms on the xy plane.
            dXY = math.sqrt(dY**2+dX**2)
            # modXY is the distance that this particular bond has to move from the center point of the two atoms.
            modXY = self.bondRadius*(2*i-n+1)*2
            # The movement is perpendicular to the direction the bonds are facing.
            modX = dY/dXY*modXY
            modY = -dX/dXY*modXY
            for j in [(1, a1), (-1, a2)]:
                # Creates one half-bond connecting to the first atom and one connecting to the second.

                # Places the half-bond 1/4 of the way to the other atom, plus modifiers resulting from multiple bonds.
                x = self.atoms[j[1]][0]+dX/4*j[0]+modX
                y = self.atoms[j[1]][1]+dY/4*j[0]+modY
                z = self.atoms[j[1]][2]+dZ/4*j[0]
                
                #Creates one half-bond
                bond = bpy.ops.mesh.primitive_cylinder_add(
                radius = self.bondRadius,
                depth = math.sqrt(dX**2+dY**2+dZ**2)/2,
                location = (x, y, z),
                rotation = (rotX, rotY, 0),
                end_fill_type = "NOTHING")
                
                # The half bond uses the material of the atom it is attached to.
                bpy.context.object.data.materials.append(bpy.data.materials.get("element_"+self.atoms[j[1]][3]))
                # Not strictly neccesary, but smooth shading looks better in this case.
                bpy.ops.object.shade_smooth()
    
    def execute(self, context):
        # Called when the user clicks the "Generate Molecule" button.
        with open(self.filepath) as lines:
            # Opens the designated file as an array of lines.

            # atomsFound is a flag used to mark when the file starts declaring the properties of atoms.
            atomsFound = False
            for line in lines:
                # Properties of atoms and bonds in .sdf files are seperated by spaces.
                props = line.split()
                # This length test makes sure that the following code doesn't cause an "index out of range" error.
                if len(props)>=2:
                    if props[0] == "M" and props[1] == "END":
                        # In .sdf files, "M END" marks that all atoms and bonds have been declared.
                        break
                    elif line.startswith("   "):
                        # Lines starting with four spaces declare an atom's properties.
                        # The properties are arranged in the format "x, y, z, symbol".
                        atomsFound = True
                        
                        # Adds the atom's properties to the list of atoms, then creates the atom.
                        self.atoms.append((float(props[0]), float(props[1]), float(props[2]), props[3]))
                        self.addAtom(props[3], float(props[0]), float(props[1]), float(props[2]))
                    elif atomsFound:
                        # After the atoms have been declared but before "M END", bonds are declared.
                        # Bonds are declared as the indices of the bonded atoms, followed by the number of bonds.
                        # Add the specified number of bonds between the specified atoms.
                        self.addBond(int(props[0])-1, int(props[1])-1, int(props[2]))
        # Tells Blender that the atom was generated successfully.
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Called when the user attempts to run the operator, asks for parameters from the user.
        context.window_manager.fileselect_add(self)
        # Tells Blender that the operator is still running pending user input.
        return {'RUNNING_MODAL'}

def register():
    # Registers the operator so that it can be used in Blender.
    bpy.utils.register_class(MolGen)

def unregister():
    # Unregisters the operator so that it can no longer be used.
    bpy.utils.unregister_class(MolGen)
