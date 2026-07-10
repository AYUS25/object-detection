"""
relationship_engine.py
======================
State-based Relationship Engine. Evaluates purely geometric relationships
between stable objects and tracks state transitions to emit events.
"""

from typing import List, Tuple, Set, Dict, Any
import spatial_engine

class RelationshipEngine:
    def __init__(self):
        # Maps (track_id_A, track_id_B) -> set of active relationships (e.g., {'near', 'A_inside_B'})
        self._active_relationships: Dict[Tuple[int, int], Set[str]] = {}

    def _is_inside_valid(self, cat_inner: str, cat_outer: str) -> bool:
        if cat_inner == 'Humans' and cat_outer in ('Electronics', 'Furniture'):
            return False
        if cat_inner == 'Furniture' and cat_outer == 'Humans':
            return False
        return True

    def _is_on_top_of_valid(self, cat_top: str, cat_bottom: str) -> bool:
        if cat_top == 'Humans' and cat_bottom == 'Electronics':
            return False
        return True

    def process(self, records: List[Any]) -> List[Tuple[int, int, str, str]]:
        """
        Evaluate relationships among stable objects.
        Returns a list of transition events: (track_id_A, track_id_B, event_type, description)
        where event_type is 'RELATIONSHIP_BEGIN' or 'RELATIONSHIP_END'.
        """
        # 1. Stability Gating: Filter for stable objects
        stable_records = [r for r in records if not r.is_new]
        
        # 2. Compute current frame relationships
        current_relationships: Dict[Tuple[int, int], Set[str]] = {}
        
        n = len(stable_records)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = stable_records[i]
                r2 = stable_records[j]
                
                # Order by track_id for consistent dictionary keys
                rec_a, rec_b = (r1, r2) if r1.track_id < r2.track_id else (r2, r1)
                pair = (rec_a.track_id, rec_b.track_id)
                
                rels = set()
                
                if spatial_engine.is_near_adaptive(rec_a.bbox, rec_b.bbox):
                    rels.add('near')
                    
                if spatial_engine.is_overlapping(rec_a.bbox, rec_b.bbox):
                    rels.add('overlapping')
                    
                if spatial_engine.is_inside(rec_a.bbox, rec_b.bbox) and self._is_inside_valid(rec_a.category, rec_b.category):
                    rels.add('A_inside_B')
                elif spatial_engine.is_inside(rec_b.bbox, rec_a.bbox) and self._is_inside_valid(rec_b.category, rec_a.category):
                    rels.add('B_inside_A')
                    
                if spatial_engine.is_on_top_of(rec_a.bbox, rec_b.bbox) and self._is_on_top_of_valid(rec_a.category, rec_b.category):
                    rels.add('A_on_top_of_B')
                elif spatial_engine.is_on_top_of(rec_b.bbox, rec_a.bbox) and self._is_on_top_of_valid(rec_b.category, rec_a.category):
                    rels.add('B_on_top_of_A')
                    
                if rels:
                    current_relationships[pair] = rels
                    
        # 3. Detect transitions (State-Based Tracking)
        events = []
        
        # Check for BEGIN events
        for pair, current_rels in current_relationships.items():
            previous_rels = self._active_relationships.get(pair, set())
            new_rels = current_rels - previous_rels
            for rel in new_rels:
                desc = self._format_desc(pair, rel, "began")
                events.append((pair[0], pair[1], "RELATIONSHIP_BEGIN", desc))
                
        # Check for END events
        for pair, previous_rels in self._active_relationships.items():
            current_rels = current_relationships.get(pair, set())
            ended_rels = previous_rels - current_rels
            for rel in ended_rels:
                desc = self._format_desc(pair, rel, "ended")
                events.append((pair[0], pair[1], "RELATIONSHIP_END", desc))
                
        # 4. Update state
        self._active_relationships = current_relationships
        
        return events

    def _format_desc(self, pair: Tuple[int, int], rel: str, action: str) -> str:
        tA, tB = pair
        if rel == 'near':
            return f"#{tA} and #{tB} {action} being near each other"
        elif rel == 'overlapping':
            return f"#{tA} and #{tB} {action} overlapping"
        elif rel == 'A_inside_B':
            return f"#{tA} {action} being inside #{tB}"
        elif rel == 'B_inside_A':
            return f"#{tB} {action} being inside #{tA}"
        elif rel == 'A_on_top_of_B':
            return f"#{tA} {action} being on top of #{tB}"
        elif rel == 'B_on_top_of_A':
            return f"#{tB} {action} being on top of #{tA}"
        return f"Unknown relationship {rel} {action}"
