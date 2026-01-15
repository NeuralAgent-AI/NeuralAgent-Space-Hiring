"""Traffic generation for satellite network simulation."""


class Packet:
    """Represents a network packet."""
    
    def __init__(self, packet_id, src, dst, created_at, ttl):
        """
        Initialize packet.
        
        Args:
            packet_id: Unique packet identifier
            src: Source node ID
            dst: Destination node ID
            created_at: Creation timestamp (seconds)
            ttl: Time to live (seconds)
        """
        self.id = packet_id
        self.src = src
        self.dst = dst
        self.created_at = created_at
        self.current_node = src
        self.ttl_remaining = ttl
        self.delivered_at = None
        self.drop_reason = None
    
    def is_delivered(self):
        """Check if packet has been delivered."""
        return self.delivered_at is not None
    
    def is_dropped(self):
        """Check if packet has been dropped."""
        return self.drop_reason is not None
    
    def is_active(self):
        """Check if packet is still in transit."""
        return not self.is_delivered() and not self.is_dropped()
    
    def move_to(self, next_node):
        """Move packet to next node."""
        self.current_node = next_node
        if self.current_node == self.dst:
            # Will be marked as delivered in simulator
            pass
    
    def decrement_ttl(self, dt):
        """Decrement TTL by dt seconds."""
        self.ttl_remaining -= dt
        if self.ttl_remaining <= 0:
            self.drop_reason = 'ttl_expired'


class TrafficGenerator:
    """Generates traffic packets for simulation."""
    
    def __init__(self, period=5, ttl=120, src='ground', dst=None):
        """
        Initialize traffic generator.
        
        Args:
            period: Packet generation period (seconds)
            ttl: Time to live for packets (seconds)
            src: Source node ID
            dst: Destination node ID (if None, will be set to first satellite)
        """
        self.period = period
        self.ttl = ttl
        self.src = src
        self.dst = dst
        self.next_packet_id = 0
        self.packets = []
    
    def set_destination(self, dst):
        """Set destination node."""
        self.dst = dst
    
    def generate_packets(self, current_time):
        """
        Generate new packets at current time.
        
        Args:
            current_time: Current simulation time (seconds)
        
        Returns:
            new_packets: List of newly created packets
        """
        new_packets = []
        
        # Generate packet if it's time
        if current_time % self.period == 0:
            packet = Packet(
                packet_id=self.next_packet_id,
                src=self.src,
                dst=self.dst,
                created_at=current_time,
                ttl=self.ttl
            )
            new_packets.append(packet)
            self.packets.append(packet)
            self.next_packet_id += 1
        
        return new_packets
    
    def get_all_packets(self):
        """Get all generated packets."""
        return self.packets
