import spacy
import networkx as nx
from typing import List, Dict, Optional
from dataclasses import dataclass
from functools import lru_cache
import logging # Added import

logger = logging.getLogger(__name__) # Added logger

@dataclass
class Section:
    title: str
    content: str
    level: int
    parent: Optional['Section']
    children: List['Section']

@dataclass
class DocumentStructure:
    sections: List[Section]
    hierarchy: 'HierarchyTree'
    metrics: Dict[str, float]

@dataclass
class NarrativeSegment:
    content: str
    type: str # Consider enhancing type detection later
    # transitions field removed as transitions are between segments

@dataclass
class NarrativeFlow:
    segments: List[NarrativeSegment]
    transitions: List[str] # List of transition types between segments i and i+1
    flow_metrics: Dict[str, float]

class HierarchyTree:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_section(self, section: Section):
        # Ensure node data includes level, handle potential missing attributes
        node_data = {'level': getattr(section, 'level', -1)}
        self.graph.add_node(section.title, **node_data)
        if section.parent:
            # Ensure parent node exists before adding edge
            if section.parent.title not in self.graph:
                 parent_data = {'level': getattr(section.parent, 'level', -1)}
                 self.graph.add_node(section.parent.title, **parent_data)
            self.graph.add_edge(section.parent.title, section.title)

    def get_depth(self) -> int:
        if not self.graph.nodes:
            return 0
        # Find root nodes (nodes with in-degree 0)
        root_nodes = [n for n, d in self.graph.in_degree() if d == 0]
        if not root_nodes:
             # Handle cases like cyclic graphs or single-node graphs if necessary
             # If only one node, depth is 0. If cyclic, depth is undefined (-1).
             return 0 if len(self.graph.nodes) <= 1 else -1

        # Calculate max depth from any root node
        max_depth = 0
        for root in root_nodes:
            try:
                # Calculate shortest path lengths from the current root
                lengths = nx.shortest_path_length(self.graph, source=root)
                # Filter out lengths if target node is not reachable (should not happen in DAG from roots)
                current_max_depth = max(lengths.values()) if lengths else 0
                max_depth = max(max_depth, current_max_depth)
            except nx.NetworkXNoPath:
                # This root might not reach all nodes (unexpected in DAG), continue
                logger.warning(f"Node {root} has no path to some nodes in the hierarchy graph.")
                continue
            except Exception as e:
                 logger.error(f"Error calculating depth from root {root}: {e}")
                 # Decide how to handle errors, maybe return -1 or raise
                 return -1 # Indicate error

        return max_depth


class StructuralAnalysisModule:
    def __init__(self):
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            logger.error("Spacy 'en_core_web_sm' model not found. Please run 'python -m spacy download en_core_web_sm'")
            # Depending on requirements, either raise an error or handle gracefully
            raise ImportError("Spacy model 'en_core_web_sm' not available.")
        self.cache_size = 1024 # Consider making this configurable

    @lru_cache(maxsize=1024)
    async def analyze_structure(self, doc_text: str) -> DocumentStructure:
        """Analyze document structure."""
        if not doc_text:
             logger.warning("analyze_structure called with empty document text.")
             # Return a default empty structure
             return DocumentStructure(sections=[], hierarchy=HierarchyTree(), metrics={})

        doc = self.nlp(doc_text)
        sections = await self._identify_sections(doc)
        hierarchy = await self._build_hierarchy(sections)
        metrics = await self._calculate_structural_metrics(hierarchy)

        return DocumentStructure(
            sections=sections,
            hierarchy=hierarchy,
            metrics=metrics
        )

    async def _identify_sections(self, doc) -> List[Section]:
        """Identify document sections based on simple heuristics."""
        # This remains a simple heuristic; more robust methods exist (e.g., ML models)
        sections = []
        current_section_sents = []
        current_level = 0 # Basic level tracking, needs improvement for nested sections
        parent_stack = [] # Stack to keep track of parent sections for hierarchy

        # Common markers that might indicate a new section/chapter heading
        section_markers = {'chapter', 'section', 'part', 'book'}
        # Regex might be better here to catch patterns like "Chapter 1", "Section II", etc.

        doc_sents = list(doc.sents)
        if not doc_sents:
            return []

        # Initialize a root section if needed, or handle documents without clear sections
        root_section = Section(title="Document Root", content="", level=-1, parent=None, children=[])
        parent_stack.append(root_section)

        for sent in doc_sents:
            is_heading = False
            # Heuristic: Check if the sentence looks like a heading (short, starts with marker, title case?)
            # Ensure sentence is not empty before accessing sent[0]
            if sent and len(sent) > 0:
                first_token_text = sent[0].text.lower()
                # Check length and if first word is a marker
                if len(sent) < 10 and first_token_text in section_markers:
                     # Basic check, could be improved with regex, POS tagging (e.g., PROPN)
                     is_heading = True
                     # TODO: Implement logic to determine heading level (e.g., based on marker, formatting)
                     new_level = current_level + 1 # Simplistic level increment
            else:
                # Skip empty sentences
                continue


            if is_heading:
                # Finalize the previous section's content block if it exists
                if current_section_sents:
                    # Find the correct parent based on level (simplified)
                    while parent_stack and parent_stack[-1].level >= new_level:
                        parent_stack.pop()
                    # Ensure parent_stack is not empty before accessing
                    parent = parent_stack[-1] if parent_stack else root_section

                    # Create the previous content section object
                    prev_section = Section(
                        title=f"{parent.title} Content Block {len(sections)}", # More specific placeholder title
                        content=' '.join(current_section_sents), # Use correct variable
                        level=parent.level + 1, # Content section level relative to parent heading
                        parent=parent,
                        children=[]
                    )
                    if parent:
                        parent.children.append(prev_section)
                    sections.append(prev_section)
                    current_section_sents = [] # Reset content for the new heading section

                # Create the new heading section
                # Find the correct parent for the heading itself
                while parent_stack and parent_stack[-1].level >= new_level:
                    parent_stack.pop()
                parent = parent_stack[-1] if parent_stack else root_section

                new_section = Section(
                    title=sent.text.strip(), # Use the sentence as title
                    content="", # Headings usually don't have content themselves
                    level=new_level,
                    parent=parent,
                    children=[]
                )
                if parent:
                    parent.children.append(new_section)
                sections.append(new_section)
                parent_stack.append(new_section) # Push new heading onto stack
                current_level = new_level # Update current level

            else:
                # Add sentence to the content of the current section
                current_section_sents.append(sent.text)

        # Add the last content block as a section
        if current_section_sents:
             parent = parent_stack[-1] if parent_stack else root_section
             last_section = Section(
                 title=f"{parent.title} Final Content Block", # Placeholder
                 content=' '.join(current_section_sents),
                 level=parent.level + 1,
                 parent=parent,
                 children=[]
             )
             if parent:
                 parent.children.append(last_section)
             sections.append(last_section)

        logger.debug(f"Identified {len(sections)} potential sections.")
        # Filter out the dummy root section if it was added and has no content/children?
        return [s for s in sections if s.level >= 0] # Return only actual document sections


    async def _build_hierarchy(self, sections: List[Section]) -> HierarchyTree:
        """Build section hierarchy from the identified sections."""
        hierarchy = HierarchyTree()
        # The section identification logic now includes parent/child relationships
        # We just need to add nodes and edges based on the Section objects
        for section in sections:
            # Use getattr to safely access attributes, provide default if missing
            node_data = {
                'level': getattr(section, 'level', -1),
                'content_length': len(getattr(section, 'content', ''))
            }
            hierarchy.graph.add_node(section.title, **node_data)

            if section.parent and getattr(section.parent, 'level', -1) >= 0: # Avoid linking to the dummy root
                # Ensure parent node exists before adding edge
                if section.parent.title not in hierarchy.graph:
                     parent_data = {'level': getattr(section.parent, 'level', -1)}
                     hierarchy.graph.add_node(section.parent.title, **parent_data)
                # Check if edge already exists? NetworkX handles this.
                hierarchy.graph.add_edge(section.parent.title, section.title)
        return hierarchy

    async def _calculate_structural_metrics(self, hierarchy: HierarchyTree) -> Dict[str, float]:
        """Calculate structural metrics."""
        num_nodes = len(hierarchy.graph.nodes)
        if num_nodes == 0:
            return {'depth': 0, 'section_count': 0, 'avg_subsections': 0}

        # Calculate average subsections (out-degree)
        avg_subsections = sum(d for n, d in hierarchy.graph.out_degree()) / num_nodes

        return {
            'depth': hierarchy.get_depth(),
            'section_count': num_nodes,
            'avg_subsections': avg_subsections
            # Add more metrics: e.g., average section length, balance factor
        }

    async def analyze_narrative_flow(self, doc_text: str) -> NarrativeFlow:
        """Analyze narrative flow."""
        if not doc_text:
             logger.warning("analyze_narrative_flow called with empty document text.")
             return NarrativeFlow(segments=[], transitions=[], flow_metrics={})

        doc = self.nlp(doc_text)
        segments = await self._identify_narrative_segments(doc)
        transitions = await self._detect_transitions(segments)
        flow_metrics = await self._calculate_flow_metrics(segments, transitions)

        return NarrativeFlow(
            segments=segments,
            transitions=transitions,
            flow_metrics=flow_metrics
        )

    async def _identify_narrative_segments(self, doc) -> List[NarrativeSegment]:
        """
        Identify narrative segments using a simple heuristic based on sentence starters
        and potential topic shifts (placeholder for more advanced methods like TextTiling).
        """
        segments = []
        current_segment_sents = []
        current_type = 'narrative'  # Default type
        # Expanded keywords for better boundary detection
        segment_boundary_keywords = {
            'however', 'meanwhile', 'therefore', 'consequently', 'next', 'then', 'finally',
            'furthermore', 'moreover', 'additionally', 'subsequently', 'thus', 'hence',
            'conversely', 'although', 'because', 'since', 'ultimately'
        }

        doc_sents = list(doc.sents) # Convert generator to list
        if not doc_sents:
             return []

        for i, sent in enumerate(doc_sents):
            # Skip empty sentences that might result from splitting
            if not sent or not sent.text.strip():
                continue

            is_boundary = False
            # Heuristic 1: Sentence starts with a transition word
            # Ensure sent has tokens before accessing sent[0]
            if len(sent) > 0 and sent[0].text.lower() in segment_boundary_keywords:
                is_boundary = True

            # Heuristic 2: Potential topic shift (Placeholder - requires better implementation)
            # if i > 0 and current_segment_sents:
            #     prev_sent = doc_sents[i-1]
            #     # ... (complex topic shift logic would go here) ...

            if is_boundary and current_segment_sents:
                # End previous segment
                segments.append(NarrativeSegment(
                    content=' '.join(current_segment_sents).strip(),
                    type=current_type, # Type detection could be enhanced here
                ))
                current_segment_sents = [sent.text] # Start new segment with the boundary sentence
            else:
                current_segment_sents.append(sent.text)

        # Add the last segment
        if current_segment_sents:
            segments.append(NarrativeSegment(
                content=' '.join(current_segment_sents).strip(),
                type=current_type,
            ))

        logger.debug(f"Identified {len(segments)} narrative segments.")
        return segments


    async def _detect_transitions(self, segments: List[NarrativeSegment]) -> List[str]:
        """Detect transitions between consecutive segments."""
        transitions = []
        if len(segments) < 2:
            return []

        # More comprehensive transition patterns
        transition_patterns = {
            'temporal': {'then', 'after', 'before', 'meanwhile', 'during', 'later', 'previously', 'subsequently', 'next', 'when', 'while', 'until'},
            'causal': {'therefore', 'thus', 'consequently', 'because', 'since', 'hence', 'as a result', 'so', 'due to'},
            'contrast': {'however', 'but', 'although', 'nonetheless', 'despite', 'yet', 'conversely', 'on the other hand', 'whereas', 'while', 'in contrast'},
            'addition': {'moreover', 'furthermore', 'additionally', 'also', 'besides', 'in addition', 'and', 'plus'},
            'summary': {'finally', 'ultimately', 'in conclusion', 'to summarize', 'in short', 'overall', 'thus'},
            'example': {'for example', 'for instance', 'specifically', 'such as', 'namely'},
            'sequence': {'first', 'second', 'third', 'next', 'then', 'finally', 'lastly'}
            # Add more categories and patterns as needed
        }

        for i in range(len(segments) - 1):
            # Look at the beginning of the *next* segment for transition cues
            next_segment_content = segments[i+1].content
            # Use spaCy to tokenize the start of the next segment for better accuracy
            # Limit analysis to avoid excessive processing on long segments
            next_segment_start_doc = self.nlp(next_segment_content[:150])
            # Look at first few tokens (adjust number as needed)
            first_tokens = [token.text.lower() for token in next_segment_start_doc[:10]]

            detected_transition_type = 'continuous' # Default if no pattern matches

            # Check for multi-word patterns first (e.g., "on the other hand", "for example")
            # Generate 2-word and 3-word phrases from the start
            start_phrase_3 = " ".join(first_tokens[:3]) if len(first_tokens) >= 3 else ""
            start_phrase_2 = " ".join(first_tokens[:2]) if len(first_tokens) >= 2 else ""

            found_multi_word = False
            # Iterate through patterns checking multi-word ones first
            for t_type, patterns in transition_patterns.items():
                 for pattern in patterns:
                     if ' ' in pattern: # Check multi-word patterns
                         # Check against 2-word and 3-word start phrases
                         if pattern == start_phrase_3 or pattern == start_phrase_2:
                             detected_transition_type = t_type
                             found_multi_word = True
                             break
                 if found_multi_word:
                     break

            # If no multi-word pattern found, check single words
            if not found_multi_word:
                for t_type, patterns in transition_patterns.items():
                    # Check single-word patterns only if they don't contain spaces
                    single_word_patterns = {p for p in patterns if ' ' not in p}
                    # Check if any of the first tokens match a single-word pattern
                    if any(word in single_word_patterns for word in first_tokens):
                        detected_transition_type = t_type
                        break # Found a match, stop checking types

            # Format: type_of_segment_i -> transition_type -> type_of_segment_i+1
            # Segment type detection is basic ('narrative'), so this simplifies
            transitions.append(f"{segments[i].type}_{detected_transition_type}_{segments[i+1].type}")

        logger.debug(f"Detected transitions: {transitions}")
        return transitions


    async def _calculate_flow_metrics(self,
                                   segments: List[NarrativeSegment],
                                   transitions: List[str]) -> Dict[str, float]:
        """Calculate narrative flow metrics."""
        num_segments = len(segments)
        if num_segments == 0:
            return {'segment_count': 0, 'avg_segment_length': 0, 'transition_diversity': 0, 'continuity_ratio': 0}

        # Calculate average segment length
        total_words = sum(len(s.content.split()) for s in segments)
        avg_segment_length = total_words / num_segments if num_segments > 0 else 0

        # Calculate transition diversity based on the detected types (e.g., temporal, causal)
        # Extract the middle part (the transition type itself)
        transition_types = [t.split('_')[1] for t in transitions if len(t.split('_')) == 3 and t.split('_')[1] != 'continuous']
        num_transitions = len(transitions)
        transition_diversity = len(set(transition_types)) / num_transitions if num_transitions > 0 else 0

        # Calculate continuity ratio (proportion of 'continuous' transitions)
        continuous_transitions = transitions.count('narrative_continuous_narrative') # Assuming default type is 'narrative'
        continuity_ratio = continuous_transitions / num_transitions if num_transitions > 0 else 1.0 # If no transitions, it's continuous

        metrics = {
            'segment_count': float(num_segments),
            'avg_segment_length': avg_segment_length,
            'transition_diversity': transition_diversity,
            'continuity_ratio': continuity_ratio
            # Add more metrics: e.g., frequency of specific transition types
        }
        # Add counts for each transition type
        for t_type in set(transition_types):
             metrics[f'{t_type}_transition_count'] = float(transition_types.count(t_type))

        return metrics


    async def generate_visualization(self, structure_analysis: DocumentStructure, narrative_flow: NarrativeFlow) -> Dict:
        """Generate visualization data including hierarchy and narrative flow."""
        vis_data = {
            'hierarchy': {
                'nodes': [],
                'edges': []
            },
            'narrative_flow': {
                'segments': [],
                'transitions': narrative_flow.transitions # Pass the raw transition strings
            },
            'metrics': {
                'structure': structure_analysis.metrics if structure_analysis else {},
                'flow': narrative_flow.flow_metrics if narrative_flow else {}
            }
        }

        # Populate hierarchy nodes and edges safely
        if structure_analysis and structure_analysis.hierarchy and structure_analysis.hierarchy.graph:
            # Convert nodes to a serializable format
            serializable_nodes = []
            for node, data in structure_analysis.hierarchy.graph.nodes(data=True):
                 serializable_nodes.append({'id': node, **data}) # Use node title as ID
            vis_data['hierarchy']['nodes'] = serializable_nodes

            # Convert edges to a serializable format
            serializable_edges = []
            for u, v in structure_analysis.hierarchy.graph.edges():
                 serializable_edges.append({'source': u, 'target': v})
            vis_data['hierarchy']['edges'] = serializable_edges

        # Populate narrative segments (potentially simplify for visualization)
        if narrative_flow and narrative_flow.segments:
            for i, segment in enumerate(narrative_flow.segments):
                 vis_data['narrative_flow']['segments'].append({
                     'id': f'seg_{i}',
                     'type': segment.type,
                     'length': len(segment.content.split()),
                     'preview': segment.content[:100] + ('...' if len(segment.content) > 100 else '') # Add a preview safely
                 })

        logger.debug("Generated visualization data.")
        return vis_data
