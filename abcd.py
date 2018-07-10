import numpy as np
import matplotlib.pyplot as plt
import warnings

class Beampath:
    """
    Defines a beampath computed by ABCD matrices using paraxial approximation
    """
    # Define plotting variables
    __col_beam = 'crimson'
    __col_object = 'tab:blue'
    __col_lens_pos = 'tab:green'
    __col_lens_neg = 'tab:orange'
    __col_image = 'purple'
    __col_exit = 'darkslategrey'
    __col_inter = 'xkcd:dull blue'
    __alpha_beam = 0.1
    __scale_vert = 0.8
    __text_offset = 0.05
    __xmin = 0
    __xmax = 1
    __ymin = -1
    __ymax = 1
    __prec = '%.2f'
    
    def __init__(self, radius=0, angle=1, index=1, position=0):
        """
        Initialise input variables
        """
        self.radius = np.array([radius])
        self.angle = np.array([angle])
        if index < 1:
            warnings.warn('Index lower than 1!')
        self.index = np.array([index])
        self.position = np.array([position])
        self.list_elements = [Object()]
        self.M = np.identity(2)
    
    def add_thinlens(self, focal_length):
        """
        Add a thin lens to the optical path and calculates the new beam parameters
        """
        self.list_elements.append(Thinlens(focal_length))
        new_rad, new_angle = np.dot(self.list_elements[-1].M, np.array([self.radius[-1], self.angle[-1]]))
        self.radius = np.append(self.radius, new_rad)
        self.angle = np.append(self.angle, new_angle)
        self.index = np.append(self.index, self.index[-1])
        self.position = np.append(self.position, self.position[-1])
        self.M = np.dot(self.list_elements[-1].M, self.M)
    
    def add_freespace(self, distance):
        """
        Add free space propagation to the optical path and calculates the new beam parameters
        """
        self.list_elements.append(Freespace(distance))
        new_rad, new_angle = np.dot(self.list_elements[-1].M, np.array([self.radius[-1], self.angle[-1]]))
        self.radius = np.append(self.radius, new_rad)
        self.angle = np.append(self.angle, new_angle)
        self.index = np.append(self.index, self.index[-1])
        self.position = np.append(self.position, self.position[-1]+distance)
        self.M = np.dot(self.list_elements[-1].M, self.M)
    
    def add_interface(self, index, curvature = np.inf):
        """
        Add an interface with a different medium to the optical path and calculates the new beam parameters
        """
        self.list_elements.append(Interface(index, self.index[-1], curvature))
        new_rad, new_angle = np.dot(self.list_elements[-1].M, np.array([self.radius[-1], self.angle[-1]]))
        self.radius = np.append(self.radius, new_rad)
        self.angle = np.append(self.angle, new_angle)
        self.index = np.append(self.index, index)
        self.position = np.append(self.position, self.position[-1])
        self.M = np.dot(self.list_elements[-1].M, self.M)
    
    def add_thicklens(self, index, thickness, radius_in=np.inf, radius_out=np.inf):
        """
        Add a thick lens to the optical path and calculates the new beam parameters
        """
        index_before = self.index[-1]
        self.add_interface(index, radius_in)
        self.add_freespace(thickness)
        self.add_interface(index_before, radius_out)
    
    def add_image(self):
        """
        Calculate the image position and add it to the beam path
        """
        beam_in = np.array([0,1])
        beam_out = np.dot(self.M, beam_in)
        # Get distance where the beam crosses the optical axis
        with np.errstate(divide='ignore'): # remove divide by zero warning
            distance_image = -beam_out[0]/beam_out[1]
        if isinstance(self.list_elements[-1], Freespace):
            self._add_exit()
        self.add_freespace(distance_image)
        self.list_elements.append(Image())
        self.radius = np.append(self.radius, self.radius[-1])
        self.angle = np.append(self.angle, self.angle[-1])
        self.index = np.append(self.index, self.index[-1])
        self.position = np.append(self.position, self.position[-1])
    
    def _add_exit(self):
        """
        Add an dummy exit plane
        """
        self.list_elements.append(Exit())
        self.radius = np.append(self.radius, self.radius[-1])
        self.angle = np.append(self.angle, self.angle[-1])
        self.index = np.append(self.index, self.index[-1])
        self.position = np.append(self.position, self.position[-1])
        


    def plot(self, **kwargs):
        """
        Plot the beam path
        """
        fig, ax = self._plot_initialise(**kwargs)
        for idx in range(len(self.list_elements)):
            self.list_elements[idx].plot(ax, idx, self, **kwargs)
        
    
    def _plot_initialise(self, **kwargs):
        fig_size = kwargs.get('figsize', (12,6))
        fig, ax = plt.subplots(figsize=fig_size) # Initialise figure
        pos = self.position[np.isfinite(self.position)]
        xrange = np.ptp(pos) # Get x range
        # Compute x and y limits
        if self.list_elements:
            self.__xmin = np.min(pos) - 0.1*xrange
            self.__xmax = np.max(pos) + 0.1*xrange
            self.__ymax = np.max(np.abs(self.radius[np.isfinite(self.radius)]))*1.5
            self.__ymin = - self.__ymax
        # Set x and y limits
        ax.set_xlim(self.__xmin, self.__xmax)
        ax.set_ylim(self.__ymin, self.__ymax)
        # Define the digit precision
        plot_digit = kwargs.get('plot_digit', None)
        if plot_digit is not None:
            self.__prec = '%.' + '%d'%plot_digit + 'f'
        # Plot optical axis
        ax.plot([self.__xmin, self.__xmax],[0, 0], ls='-.', color='grey')
        if np.any(self.index!=self.index[0]):
            ax.text(self.__xmin + 0.01*xrange, self.__ymin*(self.__text_offset+self.__scale_vert), 
                    'Index:', color = self.__col_inter, ha='left', va='top')
        return fig, ax    

    
class Element:
    """
    Abstract parent class for optical elements
    """
    def __init__(self):
        # Initialise plotting variables
        self.__color = {'beam': 'crimson',
                        'object': 'tab:blue',
                        'lens_pos': 'tab:green',
                        'lens_neg': 'tab:orange',
                        'image': 'purple',
                        'exit': 'darkslategrey',
                        'interface': 'xkcd:dull blue',
                        'axis': 'grey'}
        self.__alpha_beam = 0.1
        self.__scale_vert = 0.8
        self.__text_offset = 0.05
        self.__xmin = 0
        self.__xmax = 1
        self.__ymin = -1
        self.__ymax = 1
        self.__prec = '%.2f'
    
    def _plot_var(self, ax, **kwargs):
        self.__xmin, self.__xmax = ax.get_xlim()
        self.__ymin, self.__ymax = ax.get_ylim()
        plot_digit = kwargs.get('plot_digit', None)
        if plot_digit is not None:
            self.__prec = '%.' + '%d'%plot_digit + 'f'
        
        
class Object(Element):
    """
    Object of beam path
    """
    def __init__(self):
        super().__init__()
    
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        # Get plot variables
        self._plot_var(ax, **kwargs)
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        sc = self._Element__scale_vert
        tx = self._Element__text_offset
        col = self._Element__color['object']
        pos = beam_path.position[elem_pos]
        # Plot object
        ax.plot([pos, pos], [ymin*sc, ymax*sc], ls='--', color = col)
        ax.text(pos, ymax*(sc+tx), 'Object', color = col, ha = 'center', va = 'bottom')
    
class Thinlens(Element):
    """
    Thin lens optical element
    """
    def __init__(self, focal_length):
        super().__init__()
        self.focal_length = focal_length
        self.M = np.array([[1,0],[-1/self.focal_length, 1]])
    
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        # Get plot variables
        self._plot_var(ax, **kwargs)
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        sc = self._Element__scale_vert
        tx = self._Element__text_offset
        prec = self._Element__prec
        prec = prec[0] + '+' + prec[1:] # display signed focal length
        pos = beam_path.position[elem_pos]
        if self.focal_length < 0:
            col = self._Element__color['lens_neg']
        else:
            col = self._Element__color['lens_pos']
        # Plot lens with text
        ax.plot([pos, pos], [sc*ymin, sc*ymax], color=col)
        ax.text(pos, (sc+tx)*ymax, ('Lens\n'+prec%(self.focal_length)).rstrip('0').rstrip('.'),
                color=col, ha='center', va='bottom')
        

class Freespace(Element):
    """
    Free space propagation
    """
    def __init__(self, distance):
        super().__init__()
        self.distance = distance
        self.M = np.array([[1,distance],[0, 1]])
    
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        # Get plot variables
        self._plot_var(ax, **kwargs)
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        sc = self._Element__scale_vert
        tx = self._Element__text_offset
        col = self._Element__color['beam']
        col2 = self._Element__color['interface']
        alp = self._Element__alpha_beam
        pos = beam_path.position[elem_pos-1:elem_pos+1]
        rad = beam_path.radius[elem_pos-1:elem_pos+1]
        n = beam_path.index[elem_pos]
        prec = self._Element__prec
        # Plot beam path
        if isinstance(beam_path.list_elements[-1], Image) and elem_pos == (len(beam_path.list_elements)-2):
            line_style = ':'
        else:
            line_style = '-'
        ax.plot(pos, rad,line_style, color=col)
        ax.plot(pos, -rad,line_style, color=col)
        ax.fill_between(pos, rad, -rad, facecolor=col, alpha=alp)
        if np.any(beam_path.index!=beam_path.index[0]):
            ax.fill_between(pos, [ymax, ymax], [ymin, ymin], facecolor = col2, alpha = (1-1/n))
            ax.text(np.mean(pos), (sc+tx)*ymin, (prec%n).rstrip('0').rstrip('.'), 
                        color=col2, ha = 'center', va='top')

class Interface(Element):
    """
    Interface between two mediums
    """
    def __init__(self, index_out, index_in = 1, curvature=np.inf):
        super().__init__()
        if index_in < 1 or index_out < 1:
            warnings.warn('Index lower than 1!')
        self.index_in = index_in
        self.index_out = index_out
        self.curvature = curvature
        self.M = np.array([[1,0],[(self.index_in-self.index_out)/(self.curvature*self.index_out),
                                  self.index_in/self.index_out]])
    
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        self._plot_var(ax, **kwargs)
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        pos = beam_path.position[elem_pos]
        diff_pos = np.ptp(beam_path.position)/20
        col = self._Element__color['interface']
        if not np.isfinite(self.curvature):
            x = np.array([pos,pos])
            y = np.array([0, ymax])
        else:
            r = self.curvature
            x0 = r + pos
            x = np.linspace(-r, -r + np.sign(r)*diff_pos, num=200) + x0
            y = np.abs(r*np.sin(np.arccos(np.clip((x-x0)/r, -1,1))))
        ax.plot(x, y, color = col)
        ax.plot(x, -y, color = col)

        
class Exit(Element):
    """
    Exit plane of beam path
    """
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        # Get plot variables
        self._plot_var(ax, **kwargs)
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        sc = self._Element__scale_vert
        tx = self._Element__text_offset
        col = self._Element__color['exit']
        prec = self._Element__prec
        pos = beam_path.position[elem_pos]        
        # Plot object
        ax.plot([pos, pos], [ymin*sc, ymax*sc], ls='--', color = col)
        #ax.text(pos, ymax*(sc+tx), 'Exit plane at '+prec%pos, color = col, ha = 'center', va = 'bottom')
        
class Image(Element):
    """
    Image of beam path
    """
    
    def plot(self, ax, elem_pos, beam_path, **kwargs):
        # Get plot variables
        self._plot_var(ax, **kwargs)
        xmin = self._Element__xmin
        xmax = self._Element__xmax
        ymin = self._Element__ymin
        ymax = self._Element__ymax
        sc = self._Element__scale_vert
        tx = self._Element__text_offset
        col = self._Element__color['image']
        prec = self._Element__prec
        pos = beam_path.position[elem_pos]
        xrange = xmax-xmin
        yrange = ymax-ymin
        # Plot object
        if np.isfinite(pos):
            ax.plot([pos, pos], [ymin*sc, ymax*sc], ls='--', color=col)
            ax.text(pos, ymax*(sc+tx), ('Image at\n'+prec%pos).rstrip('0').rstrip('.'), color=col, ha='center', va='bottom')
        else:
            ax.text(xmax - 0.01*xrange, yrange*0.01, 'Image', color=col, ha='right', va='bottom')
            ax.text(xmax - 0.01*xrange, -yrange*0.01, 'at \u221E \u2192', color=col, ha='right', va='top')
