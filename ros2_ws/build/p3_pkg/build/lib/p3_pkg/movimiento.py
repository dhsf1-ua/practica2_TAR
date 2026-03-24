import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import math
import time

class RobotController(Node):
    def __init__(self, opcion):
        super().__init__('movimiento_node')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.opcion = opcion
        # Esperamos a que todo cargue antes de empezar
        self.get_logger().info(f'Iniciando opción de movimiento: {opcion}')
        time.sleep(2.0)
        self.ejecutar_logica()

    def detener(self):
        self.publisher.publish(Twist())
        time.sleep(0.5)

    def mover_lineal(self, distancia, velocidad=0.2):
        msg = Twist()
        msg.linear.x = velocidad
        tiempo = abs(distancia / velocidad)
        self.publisher.publish(msg)
        time.sleep(tiempo)
        self.detener()

    def girar(self, grados, vel_angular=0.4):
        msg = Twist()
        rad = math.radians(grados)
        msg.angular.z = vel_angular if rad > 0 else -vel_angular
        tiempo = abs(rad / vel_angular)
        self.publisher.publish(msg)
        time.sleep(tiempo)
        self.detener()

    def dibujar_circulo(self, tiempo, sentido_horario=False):
        # Para el infinito: combinación de lineal y angular
        msg = Twist()
        msg.linear.x = 0.2
        msg.angular.z = -0.4 if sentido_horario else 0.4
        self.publisher.publish(msg)
        time.sleep(tiempo)
        self.detener()

    def ejecutar_logica(self):
        if self.opcion == 0:
            self.mover_lineal(2.0)
            
        elif self.opcion == 1: # Triángulo equilátero (3m)
            for _ in range(3):
                self.mover_lineal(3.0)
                self.girar(120) # 120 grados para que el ángulo interno sea 60

        elif self.opcion == 2: # Cuadrado (1m)
            for _ in range(4):
                self.mover_lineal(1.0)
                self.girar(90)

        elif self.opcion == 3: # Infinito
            self.mover_lineal(0.5)
            self.girar(60)
            # Dibujamos dos círculos para simular el infinito
            self.dibujar_circulo(15.7, sentido_horario=False)
            self.dibujar_circulo(15.7, sentido_horario=True)

        self.get_logger().info('Movimiento completado.')
        raise SystemExit

def main():
    rclpy.init()
    if len(sys.argv) < 2:
        print("Error: Indica un número (0, 1, 2, 3)")
        return
    
    opcion = int(sys.argv[1])
    node = RobotController(opcion)
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    rclpy.shutdown()

if __name__ == '__main__':
    main()
