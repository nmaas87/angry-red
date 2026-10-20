import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ItemParser:
    """Parse item attribute data from client XML/CSV files.
    
    Loads weapon, armor, and accessory attribute data to get base item values (itemVal)
    used for sell price calculations.
    """
    
    def __init__(self):
        self.weapon_values = {}  # {item_id: value}
        self.armor_values = {}   # {item_id: value}
        self.accessory_values = {}  # {item_id: value}
        self.loaded = False
    
    def load(self, client_assets_path=None):
        """Load item attribute data from client files.
        
        Args:
            client_assets_path: Path to akaneiro-client/Assets directory.
                              Defaults to relative path from this file.
        """
        if client_assets_path is None:
            # Default path: ../akaneiro-client/Assets/Resources/Localization/EN/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            client_assets_path = os.path.join(base_dir, '..', 'akaneiro-client', 'Assets', 'Resources', 'Localization', 'EN')
        
        print(f"Loading item data from: {client_assets_path}")
        
        # Load weapon values (column 10 = Value)
        self._load_csv(client_assets_path, 'WeaponAttribute.weapon.EN.txt', 10, self.weapon_values)
        
        # Load armor values (column 4 = Value)
        self._load_csv(client_assets_path, 'ArmorAttribute.Armor.EN.txt', 4, self.armor_values)
        
        # Load accessory values (column 3 = Value)
        self._load_csv(client_assets_path, 'AccessoriesAttribute.Accessory.EN.txt', 3, self.accessory_values)
        
        self.loaded = True
        print(f"Loaded item data: {len(self.weapon_values)} weapons, {len(self.armor_values)} armors, {len(self.accessory_values)} accessories")
    
    def _load_csv(self, path, filename, value_col, target_dict):
        """Load a CSV/TXT file and extract item values.
        
        Args:
            path: Base directory path
            filename: Filename to load
            value_col: Column index for the Value field (0-based)
            target_dict: Dictionary to populate with {item_id: value}
        """
        filepath = os.path.join(path, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Skip header rows (first 2 lines are headers)
            for line in lines[2:]:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('\t')
                if len(parts) <= value_col:
                    continue
                
                try:
                    item_id = int(parts[0])  # First column is ID
                    value = float(parts[value_col])  # Value column
                    target_dict[item_id] = value
                except (ValueError, IndexError):
                    continue
            
            print(f"Loaded {len(target_dict)} items from {filename}")
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    def get_item_val(self, item_id):
        """Get the base item value (itemVal) for an item.
        
        Args:
            item_id: Item template ID (e.g., 1003 for Club, 2001 for Helm)
            
        Returns:
            Base item value as float. Returns 15.0 if not found.
        """
        if not self.loaded:
            return 15.0
        
        # Determine which dictionary to use based on item_id range
        if 1000 <= item_id < 2000:
            # Weapon
            return self.weapon_values.get(item_id, 15.0)
        elif 2000 <= item_id < 3000:
            # Armor
            return self.armor_values.get(item_id, 15.0)
        elif 3000 <= item_id < 4000:
            # Accessory
            return self.accessory_values.get(item_id, 15.0)
        
        # Default fallback
        return 15.0
    
    def calculate_sell_price(self, item_id):
        """Calculate sell price for an item using client formula.
        
        Formula: (level) * (1 + eleVal + encVal + gemVal) * (itemVal * 0.4)
        For basic items (level=1, no elements/enchants/gems): itemVal * 0.4
        
        Args:
            item_id: Item template ID
            
        Returns:
            Sell price as integer karma
        """
        if not self.loaded:
            return max(1, int(item_id // 10))
        
        item_val = self.get_item_val(item_id)
        # Basic formula for items without elements/enchants/gems
        sell_price = int(item_val * 0.4)
        return max(1, sell_price)


# Global instance
_item_parser = None


def get_item_parser():
    """Get or create the global ItemParser instance."""
    global _item_parser
    if _item_parser is None:
        _item_parser = ItemParser()
        _item_parser.load()  # Auto-load on first use
    return _item_parser
