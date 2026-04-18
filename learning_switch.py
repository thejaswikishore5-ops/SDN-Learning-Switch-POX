from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class LearningSwitch (object):
    def __init__ (self, connection):
        self.connection = connection
        connection.addListeners(self)
        # Table to store MAC address to port mappings
        self.mac_to_port = {}

    def do_forwarding (self, packet, packet_in, out_port):
        # Create the OpenFlow match-action rule
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet, packet_in.in_port)
        msg.actions.append(of.ofp_action_output(port = out_port))
        msg.data = packet_in
        self.connection.send(msg)
        log.info("Installing flow for %s -> port %i" % (packet.src, out_port))

    def _handle_PacketIn (self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        # Learn the source MAC and the port it came from
        self.mac_to_port[packet.src] = event.port

        # Check if we know the destination port
        if packet.dst in self.mac_to_port:
            self.do_forwarding(packet, event.ofp, self.mac_to_port[packet.dst])
        else:
            # Flood the packet if destination is unknown (Normal Switch Behavior)
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            self.connection.send(msg)

def launch ():
    def start_switch (event):
        log.info("Controlling switch %s" % (event.connection,))
        LearningSwitch(event.connection)
    core.openflow.addListenerByName("ConnectionUp", start_switch)
