#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import sys
import math
import time
from rclpy.qos import QoSProfile, ReliabilityPolicy


def euler_from_quaternion(x, y, z, w):
    """Convierte quaternion a ángulos de Euler (roll, pitch, yaw)."""
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return yaw


class MovimientoRobot(Node):

    def __init__(self):
        super().__init__('movimiento_robot')

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, qos)

        self.pos_x = 0.0
        self.pos_y = 0.0
        self.yaw = 0.0
        self.odom_received = False

    def odom_callback(self, msg):
        self.pos_x = msg.pose.pose.position.x
        self.pos_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.yaw = euler_from_quaternion(q.x, q.y, q.z, q.w)
        self.odom_received = True

    def wait_for_odom(self):
        """Espera hasta recibir el primer mensaje de odometría."""
        self.get_logger().info('Esperando odometría...')
        while not self.odom_received:
            rclpy.spin_once(self, timeout_sec=0.1)

    def stop(self):
        msg = Twist()
        self.publisher_.publish(msg)
        time.sleep(0.5)

    def move_linear(self, distance, speed=0.2):
        """Avanza 'distance' metros usando odometría."""
        self.wait_for_odom()
        rclpy.spin_once(self, timeout_sec=0.1)

        start_x = self.pos_x
        start_y = self.pos_y
        self.get_logger().info(f'Iniciando movimiento lineal: {distance} m')

        msg = Twist()
        msg.linear.x = speed if distance >= 0 else -speed
        target = abs(distance)

        while True:
            rclpy.spin_once(self, timeout_sec=0.05)
            traveled = math.sqrt(
                (self.pos_x - start_x) ** 2 +
                (self.pos_y - start_y) ** 2
            )
            self.publisher_.publish(msg)
            if traveled >= target:
                break

        self.stop()
        self.get_logger().info(f'Movimiento lineal completado.')

    def rotate(self, angle_rad, speed=0.5):
        """Gira 'angle_rad' radianes (positivo = izquierda/antihorario)."""
        self.wait_for_odom()
        rclpy.spin_once(self, timeout_sec=0.1)

        start_yaw = self.yaw
        target_angle = abs(angle_rad)
        direction = 1.0 if angle_rad >= 0 else -1.0
        self.get_logger().info(f'Iniciando giro: {math.degrees(angle_rad):.1f}°')

        msg = Twist()
        msg.angular.z = direction * speed
        accumulated = 0.0
        prev_yaw = start_yaw

        while True:
            rclpy.spin_once(self, timeout_sec=0.05)
            delta = self.yaw - prev_yaw

            # Normalizar delta al rango [-pi, pi]
            while delta > math.pi:
                delta -= 2 * math.pi
            while delta < -math.pi:
                delta += 2 * math.pi

            accumulated += abs(delta)
            prev_yaw = self.yaw
            self.publisher_.publish(msg)

            if accumulated >= target_angle:
                break

        self.stop()
        self.get_logger().info(f'Giro completado.')

    # ------------------------------------------------------------------
    # Movimiento 0: Avanzar 2 metros en línea recta
    # ------------------------------------------------------------------
    def mov_0_lineal(self):
        self.get_logger().info('=== MOV 0: Avance lineal 2 m ===')
        self.move_linear(2.0)

    # ------------------------------------------------------------------
    # Movimiento 1: Triángulo equilátero (lado = 3 m)
    # Ángulo exterior de un triángulo = 120° = 2π/3 rad
    # ------------------------------------------------------------------
    def mov_1_triangulo(self):
        self.get_logger().info('=== MOV 1: Triángulo equilátero (lado 3 m) ===')
        for i in range(3):
            self.get_logger().info(f'Lado {i + 1}/3')
            self.move_linear(3.0)
            self.rotate(math.radians(120))

    # ------------------------------------------------------------------
    # Movimiento 2: Cuadrado (lado = 1 m)
    # Ángulo exterior = 90° = π/2 rad
    # ------------------------------------------------------------------
    def mov_2_cuadrado(self):
        self.get_logger().info('=== MOV 2: Cuadrado (lado 1 m) ===')
        for i in range(4):
            self.get_logger().info(f'Lado {i + 1}/4')
            self.move_linear(1.0)
            self.rotate(math.radians(90))

    def mov_3_infinito(self):
        self.get_logger().info('=== MOV 3: Infinito (8 acostado) ===')

        # La figura: dos triángulos laterales unidos en el origen.
        # El robot empieza en el vértice central mirando "arriba".
        #
        # Triángulo derecho:
        #   avanzar 0.5m, girar -60° (derecha), avanzar 0.5m, girar -60°,
        #   avanzar 0.5m, girar -60° → vuelve al centro mirando "arriba" de nuevo
        #
        # Triángulo izquierdo: igual pero girando +60° (izquierda)

        # Paso inicial indicado por el enunciado
        self.move_linear(0.5)
        self.rotate(math.radians(-120))  # -60° (hacia la derecha)

        self.move_linear(1)
        self.rotate(math.radians(120))

        self.move_linear(0.5)
        self.rotate(math.radians(120))
        self.move_linear(1)



def main():
    if len(sys.argv) < 2:
        print('Uso: ros2 run p3_pkg movimiento.py <0|1|2|3>')
        print('  0: Avance lineal 2 m')
        print('  1: Triángulo equilátero (lado 3 m)')
        print('  2: Cuadrado (lado 1 m)')
        print('  3: Figura en infinito')
        sys.exit(1)

    opcion = int(sys.argv[1])

    rclpy.init()
    nodo = MovimientoRobot()

    # Dar tiempo al nodo a suscribirse y recibir odometría
    time.sleep(1.0)

    movimientos = {
        0: nodo.mov_0_lineal,
        1: nodo.mov_1_triangulo,
        2: nodo.mov_2_cuadrado,
        3: nodo.mov_3_infinito,
    }

    if opcion not in movimientos:
        nodo.get_logger().error(f'Opción inválida: {opcion}. Usa 0, 1, 2 o 3.')
        nodo.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    try:
        movimientos[opcion]()
    except KeyboardInterrupt:
        nodo.get_logger().info('Interrumpido por el usuario.')
    finally:
        nodo.stop()
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
