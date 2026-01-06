from sense_hat import SenseHat as sense
import os
import time

# Define colours (R, G, B)
O = (0, 0, 0)       # OFF
G = (0, 100, 0)
sense.low_light = True


class SenseHatManager:
    """
    A wrapper class to manage the Sense HAT's LEDs by displaying a static Flower 
    pattern, and providing CPU temperature-compensated sensor data.
    """
    def __init__(self):
        try:
            self.sense = sense()
            self.sense.low_light = True
            self.sense.clear()
            print("Sense HAT Manager initialized.")
        except Exception as e:
            print(f"Error initializing Sense HAT: {e}")
            self.sense = None
        
        # --- STATIC FLOWER PIXEL ART ---
        self.pattern = [
            G, O, O, G, G, O, O, G,
            O, G, O, G, G, O, G, O,
            O, O, G, G, G, G, O, O,
            G, G, G, O, O, G, G, G,
            G, G, G, O, O, G, G, G,
            O, O, G, G, G, G, O, O,
            O, G, O, G, G, O, G, O,
            G, O, O, G, G, O, O, G
        ]


        
        # --- SENSOR CORRECTION ---
        self.FACTOR = 1.3 

    def get_cpu_temp(self):
        """Reads the raw CPU temperature from the system."""
        try:
            # Executes system command to read CPU temperature
            res = os.popen("vcgencmd measure_temp").readline()
            return float(res.replace("temp=", "").replace("'C\n", ""))
        except Exception:
            return 0.0

    def get_sensor_data(self):
        """
        Gets the CORRECTED temperature and humidity.
        Returns: dict: {"temperature": float, "humidity": float}
        """
        if not self.sense:
            return {"temperature": 0.0, "humidity": 0.0}

        # Temperature compensation logic
        temp_humidity = self.sense.get_temperature_from_humidity()
        temp_pressure = self.sense.get_temperature_from_pressure()
        raw_sense_temp = (temp_humidity + temp_pressure) / 2
        cpu_temp = self.get_cpu_temp()
        corrected_temp = raw_sense_temp - ((cpu_temp - raw_sense_temp) / self.FACTOR)
        
        print(f" [Temp Debug] Raw: {raw_sense_temp:.1f}C | CPU: {cpu_temp:.1f}C | Corrected: {corrected_temp:.1f}C")
        
        return {
            "temperature": round(corrected_temp, 2),
            "humidity": round(self.sense.get_humidity(), 2)
        }

    def set_status(self, status):
        """
        Displays the flower pattern regardless of the status, 
        and clears the screen only if no face is detected.
        """
        if not self.sense:
            return

        s = status.upper()

        if s == "NO FACE":
             self.sense.clear()
        else:
             # Displays the flower pattern for FOCUSED, DISTRACTED, and DROWSY
             self.sense.set_pixels(self.pattern)

    def clear(self):
        """Clears the LED matrix."""
        if self.sense:
            self.sense.clear()