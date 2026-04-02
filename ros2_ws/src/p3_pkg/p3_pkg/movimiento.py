#!/usr/bin/env python3
"""
Nodo ROS2 para movimiento de robot con controlador PID en giros.

MEJORA PRINCIPAL:
  La función rotate() original acumulaba el ángulo girado sumando deltas
  de yaw (método incremental). Esto provoca error acumulado por ruido en
  odometría y slip de ruedas.

  La nueva implementación calcula el ángulo OBJETIVO absoluto y usa un
  controlador PID que ajusta continuamente la velocidad angular según:
      error = normalize(yaw_objetivo - yaw_actual)
  Esto elimina la acumulación de error y produce giros mucho más precisos.

  El mismo principio PID se aplica a move_linear() para corrección de
  trayectoria recta (el robot tiende a desviarse levemente al avanzar).

PARÁMETROS PID DE GIRO (ajusta según tu robot):
  KP_ROT = 1.8   -- Respuesta proporcional. Súbelo si el robot es lento.
  KI_ROT = 0.01  -- Elimina error residual. Mantenlo bajo para evitar wind-up.
  KD_ROT = 0.12  -- Amortigua oscilaciones al llegar al objetivo.
  TOL_ROT = 0.015 rad (~0.86°) -- Tolerancia de parada.

PARÁMETROS PID DE AVANCE (corrección de heading):
  KP_HEAD = 0.4  -- Cuánto se corrige la desviación lateral al avanzar.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import sys
import math
import time
from rclpy.qos import QoSProfile, ReliabilityPolicy


# ── Parámetros PID para rotación ─────────────────────────────────────────────
KP_ROT = 1.8       # Ganancia proporcional
KI_ROT = 0.01      # Ganancia integral
KD_ROT = 0.12      # Ganancia derivativa
TOL_ROT = 0.015    # Tolerancia de parada [rad] (~0.86°)
MAX_SPEED_ROT = 1.2  # Velocidad angular máxima [rad/s]
MIN_SPEED_ROT = 0.08 # Velocidad angular mínima (evita que el robot pare antes)

# ── Parámetros de movimiento lineal ──────────────────────────────────────────
KP_HEAD = 0.4      # Corrección de heading mientras avanza (mini-PID)
DEFAULT_LINEAR_SPEED = 0.2   # [m/s]
DEFAULT_ANGULAR_SPEED = 1.0  # [rad/s] (solo como referencia; PID lo ajusta)


def euler_from_quaternion(x, y, z, w):
    """Convierte quaternion a yaw (ángulo de rotación alrededor del eje Z)."""
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def normalize_angle(angle):
    """Normaliza un ángulo al rango [-π, π]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


class PIDController:
    """
    Controlador PID genérico.

    Uso:
        pid = PIDController(kp, ki, kd)
        pid.reset()
        output = pid.compute(error, dt)
    """

    def __init__(self, kp, ki, kd, max_output=None, min_output=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.min_output = min_output
        self.reset()

    def reset(self):
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        """
        Calcula la salida del controlador.

        Args:
            error: error actual (setpoint - medición)
            dt:    intervalo de tiempo desde la última llamada [s]

        Returns:
            Salida del controlador (velocidad, fuerza, etc.)
        """
        if dt <= 0:
            return 0.0

        # Término proporcional
        p = self.kp * error

        # Término integral 
        self._integral += error * dt
        i = self.ki * self._integral

        # Término derivativo
        if self._prev_error is None:
            d = 0.0
        else:
            d = self.kd * (error - self._prev_error) / dt

        self._prev_error = error
        output = p + i + d

        # Saturación de salida
        if self.max_output is not None:
            output = min(output, self.max_output)
        if self.min_output is not None:
            output = max(output, self.min_output)

        return output


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

        # Controlador PID para giros
        self.pid_rot = PIDController(
            kp=KP_ROT,
            ki=KI_ROT,
            kd=KD_ROT,
            max_output=MAX_SPEED_ROT,
            min_output=-MAX_SPEED_ROT,
        )

    def odom_callback(self, msg):
        self.pos_x = msg.pose.pose.position.x
        self.pos_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.yaw = euler_from_quaternion(q.x, q.y, q.z, q.w)
        self.odom_received = True

    def wait_for_odom(self):
        self.get_logger().info('Esperando odometría...')
        while not self.odom_received:
            rclpy.spin_once(self, timeout_sec=0.1)


    def stop(self):
        """Publica velocidad cero y espera para que el robot frene."""
        msg = Twist()
        self.publisher_.publish(msg)
        time.sleep(0.5)

    def move_linear(self, distance, speed=DEFAULT_LINEAR_SPEED):
        # Avanza 'distance' metros en línea recta.

        self.wait_for_odom()
        rclpy.spin_once(self, timeout_sec=0.1)

        start_x = self.pos_x
        start_y = self.pos_y
        heading_ref = self.yaw   # Heading que queremos mantener al avanzar
        target = abs(distance)
        sign = 1.0 if distance >= 0 else -1.0

        self.get_logger().info(
            f'Movimiento lineal: {distance:.2f} m  heading_ref={math.degrees(heading_ref):.1f}°')

        msg = Twist()

        while True:
            rclpy.spin_once(self, timeout_sec=0.05)

            # Distancia recorrida
            traveled = math.sqrt(
                (self.pos_x - start_x) ** 2 +
                (self.pos_y - start_y) ** 2
            )

            if traveled >= target:
                break

            # Velocidad lineal (rampa suave al frenar)
            remaining = target - traveled
            ramp = min(1.0, remaining / 0.25)   # Frena en los últimos 25 cm
            msg.linear.x = sign * speed * max(0.1, ramp)

            # Corrección proporcional de heading (evita que el robot se curve)
            heading_error = normalize_angle(heading_ref - self.yaw)
            msg.angular.z = KP_HEAD * heading_error

            self.publisher_.publish(msg)

        self.stop()
        self.get_logger().info('Movimiento lineal completado.')

    def rotate(self, angle_rad, speed=DEFAULT_ANGULAR_SPEED):
        # Gira 'angle_rad' radianes usando un controlador PID sobre el yaw absoluto.
        self.wait_for_odom()
        rclpy.spin_once(self, timeout_sec=0.1)

        # Ángulo objetivo absoluto en el espacio de yaw
        target_yaw = normalize_angle(self.yaw + angle_rad)

        self.get_logger().info(
            f'Giro PID: {math.degrees(angle_rad):.1f}°  '
            f'yaw_actual={math.degrees(self.yaw):.1f}°  '
            f'yaw_objetivo={math.degrees(target_yaw):.1f}°'
        )

        self.pid_rot.reset()
        msg = Twist()
        prev_time = time.time()
        consecutive_ok = 0   # Muestras consecutivas dentro de tolerancia

        while True:
            rclpy.spin_once(self, timeout_sec=0.02)

            now = time.time()
            dt = now - prev_time
            prev_time = now

            # Error angular normalizado 
            error = normalize_angle(target_yaw - self.yaw)

            # Comprobación de convergencia: exigimos N muestras seguidas
            # dentro de la tolerancia para evitar falsas paradas por ruido.
            if abs(error) < TOL_ROT:
                consecutive_ok += 1
                if consecutive_ok >= 5:
                    break
            else:
                consecutive_ok = 0

            # Salida PID - velocidad angular
            omega = self.pid_rot.compute(error, dt)

            # Velocidad mínima para vencer la fricción estática
            if abs(omega) > 1e-3:
                sign = 1.0 if omega > 0 else -1.0
                omega = sign * max(abs(omega), MIN_SPEED_ROT)

            msg.angular.z = omega
            msg.linear.x = 0.0
            self.publisher_.publish(msg)

        self.stop()
        self.get_logger().info(
            f'Giro completado. yaw_final={math.degrees(self.yaw):.1f}°  '
            f'error_residual={math.degrees(normalize_angle(target_yaw - self.yaw)):.2f}°'
        )

    # Figuras

    def mov_0_lineal(self, repeticiones=1):
        self.get_logger().info(f'=== MOV 0: Avance lineal 2 m (x{repeticiones}) ===')
        for r in range(repeticiones):
            self.get_logger().info(f'Repetición {r + 1}/{repeticiones}')
            self.move_linear(2.0)

    def mov_1_triangulo(self, repeticiones=1):
        self.get_logger().info(f'=== MOV 1: Triángulo equilátero lado 3 m (x{repeticiones}) ===')
        for r in range(repeticiones):
            self.get_logger().info(f'Repetición {r + 1}/{repeticiones}')
            for i in range(3):
                self.get_logger().info(f'Lado {i + 1}/3')
                self.move_linear(3.0)
                self.rotate(math.radians(120))

    def mov_2_cuadrado(self, repeticiones=1):
        self.get_logger().info(f'=== MOV 2: Cuadrado lado 1 m (x{repeticiones}) ===')
        for r in range(repeticiones):
            self.get_logger().info(f'Repetición {r + 1}/{repeticiones}')
            for i in range(4):
                self.get_logger().info(f'Lado {i + 1}/4')
                self.move_linear(1.0)
                self.rotate(math.radians(90))

    def mov_3_infinito(self, repeticiones=1):
        self.get_logger().info(f'=== MOV 3: Infinito (x{repeticiones}) ===')
        for r in range(repeticiones):
            self.get_logger().info(f'Repetición {r + 1}/{repeticiones}')
            self.move_linear(0.5)
            self.rotate(math.radians(-120))
            self.move_linear(1.0)
            self.rotate(math.radians(120))
            self.move_linear(0.5)
            self.rotate(math.radians(120))
            self.move_linear(1.0)
            self.rotate(math.radians(-120))


def main():
    if len(sys.argv) < 2:
        print('Uso: ros2 run p3_pkg movimiento_pid.py <0|1|2|3> [repeticiones]')
        print('  0: Avance lineal 2 m')
        print('  1: Triángulo equilátero (lado 3 m)')
        print('  2: Cuadrado (lado 1 m)')
        print('  3: Figura en infinito')
        print('  repeticiones: veces a repetir la figura (por defecto 1)')
        sys.exit(1)

    opcion = int(sys.argv[1])
    repeticiones = int(sys.argv[2]) if len(sys.argv) >= 3 else 1

    if repeticiones < 1:
        print('Error: el número de repeticiones debe ser al menos 1.')
        sys.exit(1)

    rclpy.init()
    nodo = MovimientoRobot()
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
        movimientos[opcion](repeticiones)
    except KeyboardInterrupt:
        nodo.get_logger().info('Interrumpido por el usuario.')
    finally:
        nodo.stop()
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
