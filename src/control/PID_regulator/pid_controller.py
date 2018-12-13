from time import sleep

from src.control.PID_regulator.pid import PID
import time

# todo change to 1 - 0.5 % of first error rate
THRESHOLD = 0.2


# better higher P and lower I, but matlab claims different things - only I-component


class PIDController:
    def __init__(self, position_detector, raw_controller, stiffness_function,
                 P=0.7, I=0.2, D=0.2, interception_moment=None):
        self.pid = PID(P=P, I=I, D=D)
        self.position_detector = position_detector
        self.raw_controller = raw_controller
        # todo evaluate function from string
        self.stiffness_function = stiffness_function
        self.interception_moment = interception_moment

    # def get_current_stiffness_index(self, current_angle, tick):
    #     index = int(current_angle / tick)
    #     return index

    def wait_for_interception(self, starting_angle, target_angle):
        """Wait until arm is close enough to target angle.

        Reads current arm angle from PositionDetector.
        If the arm travelled more than some ratio of the distance
        between starting_angle and target_angle, method returns.
        That ratio must be specified in self.interception_moment.

        Args:
            starting_angle:   angle in which arm started
            target_angle:     angle that we want to move the arm to

        """
        distance = abs(target_angle - starting_angle)
        while True:
            current_angle = self.position_detector.get_angle()
            movement_completion = 1 - abs(current_angle - target_angle) / distance
            if movement_completion > self.interception_moment:
                return
            sleep(0.001)

    def control(self, target_angle, starting_servo_angle, target_stiffness, starting_position):
        self.pid.set_point(target_angle)
        starting_stiffness = 0
        current_servo_angle = starting_servo_angle
        print(current_servo_angle)
        while True:
            current_angle = self.position_detector.get_angle()
            print(current_angle)

            # calculate stiffness
            movement_completion = ((current_angle + starting_position) / abs(target_angle - starting_position))
            stiffness = (self.stiffness_function(movement_completion) * (target_stiffness - starting_stiffness)) + \
                        starting_stiffness

            if abs(current_angle - target_angle) <= THRESHOLD:
                return

            delta_angle = self.pid.update(current_angle)
            print(delta_angle)
            current_servo_angle -= delta_angle

            self.raw_controller.send(int(current_servo_angle), stiffness)
            time.sleep(0.5)
