import pygame
import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import sys

class Planet:
    def __init__(self, radius, orbit_radius, orbit_speed, rotation_speed, color, name="", is_custom=False):
        self.radius = radius
        self.orbit_radius = orbit_radius
        self.orbit_speed = orbit_speed
        self.rotation_speed = rotation_speed
        self.color = color
        self.current_angle = 0.0
        self.name = name
        self.is_custom = is_custom
        
        # For custom masses
        self.position = [0.0, 0.0, 0.0]  # x, y, z position
        self.velocity = [0.0, 0.0, 0.0]  # velocity for physics
        self.mass = radius ** 3  # Mass proportional to volume

class CustomMass:
    def __init__(self, x, z, mass, color=(0.8, 0.2, 0.8)):
        self.position = [x, 0.0, z]
        self.mass = mass
        self.radius = (mass ** (1/3)) * 0.5  # Radius based on mass
        self.color = color
        self.velocity = [0.0, 0.0, 0.0]
        self.is_selected = False
        self.trail = []  # For drawing trails

class SolarSystemSimulation:
    def __init__(self, width=1200, height=800):
        self.width = width
        self.height = height
        
        # Camera controls
        self.camera_angle_x = 30.0
        self.camera_angle_y = 0.0
        self.camera_distance = 50.0
        self.mouse_pressed = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Animation
        self.time_speed = 1.0
        self.current_time = 0.0
        self.paused = False
        
        # Grid parameters
        self.grid_size = 80
        self.grid_spacing = 0.6
        self.grid_heights = np.zeros((self.grid_size, self.grid_size))
        
        # Custom masses system
        self.custom_masses = []
        self.selected_mass = None
        self.spawn_mode = False
        self.spawn_mass = 5.0
        self.show_trails = True
        self.physics_enabled = True
        
        # Initialize planets
        self.planets = []
        self.init_planets()
        
        # Store original planet data for reset
        self.original_planets = []
        for planet in self.planets:
            self.original_planets.append({
                'angle': planet.current_angle,
                'orbit_radius': planet.orbit_radius,
                'orbit_speed': planet.orbit_speed
            })
        
        # Initialize Pygame and OpenGL
        self.init_display()
        self.setup_opengl()
        
    def init_planets(self):
        """Initialize all planets in the solar system"""
        # Sun (stationary at center)
        self.planets.append(Planet(2.0, 0.0, 0.0, 0.1, (1.0, 1.0, 0.2), "Sun"))
        
        # Mercury
        self.planets.append(Planet(0.3, 5.0, 2.0, 0.5, (0.8, 0.7, 0.6), "Mercury"))
        
        # Venus
        self.planets.append(Planet(0.5, 7.0, 1.5, 0.3, (1.0, 0.8, 0.4), "Venus"))
        
        # Earth
        self.planets.append(Planet(0.6, 10.0, 1.0, 0.8, (0.2, 0.5, 1.0), "Earth"))
        
        # Mars
        self.planets.append(Planet(0.4, 13.0, 0.8, 0.7, (1.0, 0.3, 0.2), "Mars"))
        
        # Jupiter
        self.planets.append(Planet(1.5, 18.0, 0.5, 1.2, (1.0, 0.7, 0.3), "Jupiter"))
        
        # Saturn
        self.planets.append(Planet(1.2, 23.0, 0.3, 1.0, (1.0, 0.9, 0.6), "Saturn"))
        
        # Uranus
        self.planets.append(Planet(0.8, 28.0, 0.2, 0.6, (0.4, 0.8, 1.0), "Uranus"))
        
        # Neptune
        self.planets.append(Planet(0.7, 33.0, 0.15, 0.5, (0.2, 0.3, 1.0), "Neptune"))
    
    def init_display(self):
        """Initialize Pygame display"""
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("Interactive Solar System - Spawn Custom Masses!")
        
    def setup_opengl(self):
        #Configure OpenGL settings
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        
        # Set up perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45.0, self.width / self.height, 1.0, 200.0)
        glMatrixMode(GL_MODELVIEW)
        
        # Background color
        glClearColor(0.0, 0.0, 0.1, 1.0)
        
        # Lighting setup
        light_pos = [0.0, 0.0, 0.0, 1.0]
        light_ambient = [0.2, 0.2, 0.2, 1.0]
        light_diffuse = [1.0, 1.0, 0.9, 1.0]
        light_specular = [1.0, 1.0, 1.0, 1.0]
        
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
        
        # Material properties
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialfv(GL_FRONT, GL_SHININESS, [50.0])
        
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
    
    def world_to_screen(self, world_pos):
        #Convert world coordinates to screen coordinates
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        
        screen_pos = gluProject(world_pos[0], world_pos[1], world_pos[2], 
                               modelview, projection, viewport)
        return screen_pos[:2]
    
    def screen_to_world(self, screen_x, screen_y):
        #Convert screen coordinates to world coordinates on the ground plane
        # Get current matrices
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        
        # Convert screen Y (pygame uses top-left origin, OpenGL uses bottom-left)
        opengl_y = viewport[3] - screen_y
        
        # Unproject to get world coordinates at depth 0.5 (middle of view)
        try:
            near_point = gluUnProject(screen_x, opengl_y, 0.0, modelview, projection, viewport)
            far_point = gluUnProject(screen_x, opengl_y, 1.0, modelview, projection, viewport)
            
            # Find intersection with y=0 plane
            if abs(far_point[1] - near_point[1]) > 0.001:
                t = -near_point[1] / (far_point[1] - near_point[1])
                world_x = near_point[0] + t * (far_point[0] - near_point[0])
                world_z = near_point[2] + t * (far_point[2] - near_point[2])
                return [world_x, 0.0, world_z]
        except:
            pass
        
        return [0.0, 0.0, 0.0]
    
    def spawn_custom_mass(self, x, z):
        #Spawn a new custom mass at the specified position
        colors = [
            (0.8, 0.2, 0.8),  # Purple
            (1.0, 0.5, 0.0),  # Orange
            (0.0, 1.0, 0.5),  # Green
            (1.0, 0.2, 0.2),  # Red
            (0.5, 0.5, 1.0),  # Light Blue
        ]
        color = colors[len(self.custom_masses) % len(colors)]
        
        custom_mass = CustomMass(x, z, self.spawn_mass, color)
        self.custom_masses.append(custom_mass)
        print(f"Spawned mass {len(self.custom_masses)} at ({x:.1f}, {z:.1f}) with mass {self.spawn_mass}")
    
    def find_nearest_mass(self, world_pos, max_distance=2.0):
        #Find the nearest custom mass to the given world position
        nearest = None
        min_distance = max_distance
        
        for mass in self.custom_masses:
            dx = mass.position[0] - world_pos[0]
            dz = mass.position[2] - world_pos[2]
            distance = math.sqrt(dx*dx + dz*dz)
            
            if distance < min_distance:
                min_distance = distance
                nearest = mass
        
        return nearest
    
    def apply_gravitational_forces(self, dt):
        #Apply gravitational forces between custom masses and affect planets
        if not self.physics_enabled:
            return
            
        G = 0.1  # Gravitational constant (scaled for simulation)
        
        # Apply forces between custom masses
        for i, mass1 in enumerate(self.custom_masses):
            force_x, force_z = 0.0, 0.0
            
            # Force from other custom masses
            for j, mass2 in enumerate(self.custom_masses):
                if i != j:
                    dx = mass2.position[0] - mass1.position[0]
                    dz = mass2.position[2] - mass1.position[2]
                    distance = math.sqrt(dx*dx + dz*dz)
                    
                    if distance > 0.1:  # Avoid division by zero
                        force_magnitude = G * mass1.mass * mass2.mass / (distance**2)
                        force_x += force_magnitude * dx / distance
                        force_z += force_magnitude * dz / distance
            
            # Force from sun
            dx = 0 - mass1.position[0]  # Sun at origin
            dz = 0 - mass1.position[2]
            distance = math.sqrt(dx*dx + dz*dz)
            
            if distance > 0.1:
                sun_mass = self.planets[0].radius ** 3 * 10  # Sun is much more massive
                force_magnitude = G * mass1.mass * sun_mass / (distance**2)
                force_x += force_magnitude * dx / distance
                force_z += force_magnitude * dz / distance
            
            # Update velocity based on force (F = ma, so a = F/m)
            mass1.velocity[0] += (force_x / mass1.mass) * dt
            mass1.velocity[2] += (force_z / mass1.mass) * dt
            
            # Apply velocity damping to prevent runaway speeds
            damping = 0.999
            mass1.velocity[0] *= damping
            mass1.velocity[2] *= damping
            
            # Update position
            mass1.position[0] += mass1.velocity[0] * dt
            mass1.position[2] += mass1.velocity[2] * dt
            
            # Add to trail
            if len(mass1.trail) > 100:  # Limit trail length
                mass1.trail.pop(0)
            mass1.trail.append([mass1.position[0], mass1.position[2]])
        
        # Affect planet orbits (simplified perturbation)
        for planet in self.planets[1:]:  # Skip sun
            total_perturbation_x, total_perturbation_z = 0.0, 0.0
            
            planet_x = planet.orbit_radius * math.cos(planet.current_angle)
            planet_z = planet.orbit_radius * math.sin(planet.current_angle)
            
            for mass in self.custom_masses:
                dx = mass.position[0] - planet_x
                dz = mass.position[2] - planet_z
                distance = math.sqrt(dx*dx + dz*dz)
                
                if distance > 0.1:
                    # Simple perturbation effect
                    perturbation_strength = mass.mass / (distance**2) * 0.001
                    total_perturbation_x += perturbation_strength * dx / distance
                    total_perturbation_z += perturbation_strength * dz / distance
            
            # Apply small orbital perturbations
            if abs(total_perturbation_x) > 0.001 or abs(total_perturbation_z) > 0.001:
                # Slightly modify orbit speed and radius
                planet.orbit_speed *= (1 + total_perturbation_x * 0.01)
                planet.orbit_radius *= (1 + total_perturbation_z * 0.001)
    
    def draw_sphere(self, radius, slices=20, stacks=20):
        #Draw a sphere using GLU
        quadric = gluNewQuadric()
        gluSphere(quadric, radius, slices, stacks)
        gluDeleteQuadric(quadric)
    
    def update_spacetime_grid(self):
        #Update the spacetime grid based on planetary masses and custom masses
        # Reset grid
        self.grid_heights.fill(0.0)
        
        # Calculate spacetime curvature from planets
        for planet in self.planets:
            if planet.orbit_radius == 0:
                # Sun at center
                planet_x, planet_z = 0, 0
            else:
                planet_x = planet.orbit_radius * math.cos(planet.current_angle)
                planet_z = planet.orbit_radius * math.sin(planet.current_angle)
            
            self._add_mass_to_grid(planet_x, planet_z, planet.radius ** 2)
        
        # Add custom masses to grid
        for mass in self.custom_masses:
            self._add_mass_to_grid(mass.position[0], mass.position[2], mass.mass)
    
    def _add_mass_to_grid(self, x, z, mass):
        #Helper function to add a mass's effect to the spacetime grid
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                grid_x = (i - self.grid_size // 2) * self.grid_spacing
                grid_z = (j - self.grid_size // 2) * self.grid_spacing
                
                distance = math.sqrt((grid_x - x)**2 + (grid_z - z)**2)
                distance = max(distance, 0.1)  # Prevent division by zero
                
                # Gravitational well effect
                curvature = -mass / (distance ** 2) * 2.0
                self.grid_heights[i][j] += curvature
    
    def draw_spacetime_grid(self):
        #Draw the 2D spacetime grid
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.8)
        glLineWidth(1.0)
        
        # Draw grid lines
        glBegin(GL_LINES)
        for i in range(self.grid_size - 1):
            for j in range(self.grid_size - 1):
                x1 = (i - self.grid_size // 2) * self.grid_spacing
                z1 = (j - self.grid_size // 2) * self.grid_spacing
                x2 = (i + 1 - self.grid_size // 2) * self.grid_spacing
                z2 = (j + 1 - self.grid_size // 2) * self.grid_spacing
                
                # Horizontal lines
                glVertex3f(x1, self.grid_heights[i][j], z1)
                glVertex3f(x2, self.grid_heights[i+1][j], z1)
                
                # Vertical lines
                glVertex3f(x1, self.grid_heights[i][j], z1)
                glVertex3f(x1, self.grid_heights[i][j+1], z2)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def draw_orbits(self):
        #Draw orbital paths
        glDisable(GL_LIGHTING)
        glColor3f(0.5, 0.5, 0.5)
        glLineWidth(1.0)
        
        for planet in self.planets[1:]:  # Skip sun
            glBegin(GL_LINE_LOOP)
            for i in range(100):
                angle = 2.0 * math.pi * i / 100.0
                x = planet.orbit_radius * math.cos(angle)
                z = planet.orbit_radius * math.sin(angle)
                glVertex3f(x, 0, z)
            glEnd()
        
        glEnable(GL_LIGHTING)
    
    def draw_planets(self):
        #Draw all planets
        for i, planet in enumerate(self.planets):
            glPushMatrix()
            
            if i == 0:  # Sun
                # Add glow effect
                glDisable(GL_LIGHTING)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glColor4f(1.0, 1.0, 0.5, 0.3)
                self.draw_sphere(planet.radius * 1.2)
                glDisable(GL_BLEND)
                glEnable(GL_LIGHTING)
                
                glColor3f(*planet.color)
                self.draw_sphere(planet.radius)
            else:
                # Orbiting planets
                x = planet.orbit_radius * math.cos(planet.current_angle)
                z = planet.orbit_radius * math.sin(planet.current_angle)
                
                glTranslatef(x, 0, z)
                glRotatef(self.current_time * planet.rotation_speed * 50, 0, 1, 0)
                
                glColor3f(*planet.color)
                self.draw_sphere(planet.radius)
            
            glPopMatrix()
    
    def draw_custom_masses(self):
        #Draw custom masses and their trails
        glDisable(GL_LIGHTING)
        
        # Draw trails
        if self.show_trails:
            glLineWidth(2.0)
            for mass in self.custom_masses:
                if len(mass.trail) > 1:
                    glColor3f(*mass.color)
                    glBegin(GL_LINE_STRIP)
                    for point in mass.trail:
                        glVertex3f(point[0], 0, point[1])
                    glEnd()
        
        glEnable(GL_LIGHTING)
        
        # Draw masses
        for mass in self.custom_masses:
            glPushMatrix()
            glTranslatef(mass.position[0], mass.position[1], mass.position[2])
            
            # Highlight selected mass
            if mass.is_selected:
                glDisable(GL_LIGHTING)
                glColor3f(1.0, 1.0, 1.0)
                self.draw_sphere(mass.radius * 1.3)
                glEnable(GL_LIGHTING)
            
            glColor3f(*mass.color)
            self.draw_sphere(mass.radius)
            glPopMatrix()
    
    def draw_ui_text(self):
        #Draw UI information
        # This would require additional text rendering setup
        # For now, we'll print to console instead of drawing on screen
        pass
    
    def handle_input(self):
        #Handle user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.camera_distance = max(10, self.camera_distance - 2)
                elif event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE:
                    self.camera_distance = min(100, self.camera_distance + 2)
                elif event.key == pygame.K_f:
                    self.time_speed = min(5.0, self.time_speed + 0.5)
                elif event.key == pygame.K_s:
                    self.time_speed = max(0.5, self.time_speed - 0.5)
                elif event.key == pygame.K_r:
                    self.reset_simulation()
                elif event.key == pygame.K_c:
                    self.custom_masses.clear()
                    print("Cleared all custom masses")
                elif event.key == pygame.K_m:
                    self.spawn_mode = not self.spawn_mode
                    print(f"Spawn mode: {'ON' if self.spawn_mode else 'OFF'}")
                elif event.key == pygame.K_t:
                    self.show_trails = not self.show_trails
                    print(f"Trails: {'ON' if self.show_trails else 'OFF'}")
                elif event.key == pygame.K_p:
                    self.physics_enabled = not self.physics_enabled
                    print(f"Physics: {'ON' if self.physics_enabled else 'OFF'}")
                elif event.key == pygame.K_1:
                    self.spawn_mass = 1.0
                    print(f"Spawn mass set to: {self.spawn_mass}")
                elif event.key == pygame.K_2:
                    self.spawn_mass = 5.0
                    print(f"Spawn mass set to: {self.spawn_mass}")
                elif event.key == pygame.K_3:
                    self.spawn_mass = 10.0
                    print(f"Spawn mass set to: {self.spawn_mass}")
                elif event.key == pygame.K_4:
                    self.spawn_mass = 20.0
                    print(f"Spawn mass set to: {self.spawn_mass}")
                elif event.key == pygame.K_5:
                    self.spawn_mass = 50.0
                    print(f"Spawn mass set to: {self.spawn_mass}")
                elif event.key == pygame.K_DELETE:
                    if self.selected_mass:
                        self.custom_masses.remove(self.selected_mass)
                        print("Deleted selected mass")
                        self.selected_mass = None
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    if self.spawn_mode:
                        # Spawn mass at clicked location
                        world_pos = self.screen_to_world(event.pos[0], event.pos[1])
                        self.spawn_custom_mass(world_pos[0], world_pos[2])
                    else:
                        # Select mass or start camera rotation
                        world_pos = self.screen_to_world(event.pos[0], event.pos[1])
                        nearest_mass = self.find_nearest_mass(world_pos)
                        
                        if nearest_mass:
                            # Deselect previous mass
                            if self.selected_mass:
                                self.selected_mass.is_selected = False
                            
                            # Select new mass
                            self.selected_mass = nearest_mass
                            nearest_mass.is_selected = True
                            print(f"Selected mass with mass: {nearest_mass.mass}")
                        else:
                            # Start camera rotation
                            self.mouse_pressed = True
                            self.last_mouse_x, self.last_mouse_y = event.pos
                
                elif event.button == 3:  # Right mouse button
                    # Move selected mass
                    if self.selected_mass:
                        world_pos = self.screen_to_world(event.pos[0], event.pos[1])
                        self.selected_mass.position[0] = world_pos[0]
                        self.selected_mass.position[2] = world_pos[2]
                        self.selected_mass.velocity = [0.0, 0.0, 0.0]  # Reset velocity
                        self.selected_mass.trail.clear()  # Clear trail
                        print(f"Moved selected mass to ({world_pos[0]:.1f}, {world_pos[2]:.1f})")
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_pressed = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_pressed and not self.spawn_mode:
                    dx = event.pos[0] - self.last_mouse_x
                    dy = event.pos[1] - self.last_mouse_y
                    
                    self.camera_angle_y += dx * 0.5
                    self.camera_angle_x += dy * 0.5
                    
                    # Clamp vertical rotation
                    self.camera_angle_x = max(-90, min(90, self.camera_angle_x))
                    
                    self.last_mouse_x, self.last_mouse_y = event.pos
        
        return True
    
    def reset_simulation(self):
        #Reset simulation to initial state
        self.current_time = 0
        self.custom_masses.clear()
        self.selected_mass = None
        
        # Reset planets to original state
        for i, planet in enumerate(self.planets):
            planet.current_angle = self.original_planets[i]['angle']
            planet.orbit_radius = self.original_planets[i]['orbit_radius']
            planet.orbit_speed = self.original_planets[i]['orbit_speed']
        
        print("Simulation reset")
    
    def update(self, dt):
        #Update simulation state
        if not self.paused:
            self.current_time += dt * self.time_speed
            
            # Update planet positions
            for planet in self.planets[1:]:  # Skip sun
                planet.current_angle += planet.orbit_speed * dt * self.time_speed
                if planet.current_angle > 2 * math.pi:
                    planet.current_angle -= 2 * math.pi
            
            # Apply gravitational physics
            self.apply_gravitational_forces(dt * self.time_speed)
            
            # Update spacetime grid
            self.update_spacetime_grid()
    
    def render(self):
        #Render the scene
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Set up camera
        glTranslatef(0, 0, -self.camera_distance)
        glRotatef(self.camera_angle_x, 1, 0, 0)
        glRotatef(self.camera_angle_y, 0, 1, 0)
        
        # Draw scene
        self.draw_spacetime_grid()
        self.draw_orbits()
        self.draw_planets()
        self.draw_custom_masses()
        
        pygame.display.flip()
    
    def print_controls(self):
        #Print control instructions
        print("\n=== INTERACTIVE SOLAR SYSTEM CONTROLS ===")
        print("CAMERA:")
        print("  Mouse drag: Rotate view")
        print("  +/-: Zoom in/out")
        print("")
        print("SIMULATION:")
        print("  Space: Pause/unpause")
        print("  F/S: Speed up/slow down")
        print("  R: Reset simulation")
        print("")
        print("CUSTOM MASSES:")
        print("  M: Toggle spawn mode ON/OFF")
        print("  Left click: Spawn mass (spawn mode) / Select mass (normal mode)")
        print("  Right click: Move selected mass to cursor")
        print("  Delete: Remove selected mass")
        print("  C: Clear all custom masses")
        print("")
        print("MASS SIZES (1-5 keys):")
        print("  1: Small (1.0)    2: Medium (5.0)    3: Large (10.0)")
        print("  4: Huge (20.0)    5: Massive (50.0)")
        print("")
        print("OPTIONS:")
        print("  T: Toggle trails")
        print("  P: Toggle physics")
        print("  ESC: Exit")
        print(f"\nCurrent spawn mass: {self.spawn_mass}")
        print(f"Spawn mode: {'ON - Click to spawn!' if self.spawn_mode else 'OFF'}")
    
    def run(self):
        #Main game loop
        self.print_controls()
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt = clock.tick(60) / 1000.0  # Delta time in seconds
            
            running = self.handle_input()
            self.update(dt)
            self.render()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    simulation = SolarSystemSimulation()
    simulation.run()
