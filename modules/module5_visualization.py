"""
Module 5: Caldera Ability Flow Visualization
Visualize execution order and dependencies of Caldera abilities
"""

import yaml
import os
from pathlib import Path
from graphviz import Digraph
from typing import Dict, List
import sys


class AbilityFlowVisualizer:
    def __init__(self):
        # Tactic colors
        self.tactic_colors = {
            'reconnaissance': '#E8F5E9',
            'initial-access': '#FFE0B2',
            'initial_access': '#FFE0B2',
            'execution': '#FFCCBC',
            'persistence': '#F8BBD0',
            'privilege-escalation': '#E1BEE7',
            'privilege_escalation': '#E1BEE7',
            'defense-evasion': '#D1C4E9',
            'defense_evasion': '#D1C4E9',
            'credential-access': '#C5CAE9',
            'credential_access': '#C5CAE9',
            'discovery': '#BBDEFB',
            'lateral-movement': '#B3E5FC',
            'lateral_movement': '#B3E5FC',
            'collection': '#B2EBF2',
            'command-and-control': '#B2DFDB',
            'command_and_control': '#B2DFDB',
            'exfiltration': '#C8E6C9',
            'impact': '#FFCDD2'
        }

    def visualize_abilities(self, abilities_file: str, adversaries_file: str, output_dir: str):
        """Visualize Caldera ability execution flow"""
        print("\n[Step 5] Ability Flow Visualization started...")

        # Load abilities and adversaries
        with open(abilities_file, 'r', encoding='utf-8') as f:
            abilities = yaml.safe_load(f)

        with open(adversaries_file, 'r', encoding='utf-8') as f:
            adversaries = yaml.safe_load(f)

        # Handle both list and dict formats
        if isinstance(abilities, dict):
            abilities = abilities.get('abilities', [])
        if isinstance(adversaries, dict):
            adversaries = adversaries.get('adversaries', [])

        if not adversaries:
            print("  [WARNING] No adversaries found")
            return

        adversary = adversaries[0]
        adversary_name = adversary.get('name', 'Unknown')

        print(f"  Adversary: {adversary_name}")
        print(f"  Total abilities: {len(abilities)}")

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Build ability lookup
        ability_lookup = {a['ability_id']: a for a in abilities}

        # Visualize execution order
        self._visualize_execution_order(adversary, ability_lookup, output_dir)

        # Visualize dependencies
        self._visualize_dependencies(abilities, output_dir)

        # Visualize tactic flow
        self._visualize_tactic_flow(abilities, adversary, output_dir)

        print(f"[SUCCESS] Visualization completed -> {output_dir}")

    def _visualize_execution_order(self, adversary: Dict, ability_lookup: Dict, output_dir: str):
        """Visualize adversary execution order"""
        print("  [Creating execution order graph...]")

        atomic_ordering = adversary.get('atomic_ordering', [])
        adversary_name = adversary.get('name', 'Unknown')

        if not atomic_ordering:
            print("    [WARNING] No atomic_ordering found")
            return

        # Create graph
        dot = Digraph(comment='Execution Order')
        dot.attr(rankdir='TB')
        dot.attr('node', fontname='Malgun Gothic', fontsize='10', margin='0.3,0.2')
        dot.attr('edge', color='#666666', arrowsize='0.8')
        dot.attr(nodesep='0.5', ranksep='0.8')

        # Title
        dot.attr(label=f'Execution Order: {adversary_name}\\n({len(atomic_ordering)} abilities)',
                fontsize='14', fontname='Malgun Gothic', labelloc='t')

        # Add nodes
        for i, ability_id in enumerate(atomic_ordering):
            ability = ability_lookup.get(ability_id)
            if not ability:
                continue

            name = ability.get('name', 'Unknown')
            tactic = ability.get('tactic', 'unknown')
            tech_id = ability.get('technique_id', 'T0000')

            # Get color based on tactic
            color = self.tactic_colors.get(tactic, '#E0E0E0')

            label = f"{i+1}. {name}\\n{tech_id} ({tactic})"
            dot.node(f"ability_{i}", label, shape='box', style='rounded,filled',
                    fillcolor=color)

        # Add edges
        for i in range(len(atomic_ordering) - 1):
            dot.edge(f"ability_{i}", f"ability_{i+1}")

        # Add legend
        with dot.subgraph(name='cluster_legend') as legend:
            legend.attr(label='Tactics', fontname='Malgun Gothic', fontsize='10', style='dashed')
            legend.node('legend_exec', 'Execution', shape='box', style='rounded,filled',
                       fillcolor=self.tactic_colors.get('execution', '#E0E0E0'))
            legend.node('legend_priv', 'Privilege Escalation', shape='box', style='rounded,filled',
                       fillcolor=self.tactic_colors.get('privilege-escalation', '#E0E0E0'))
            legend.node('legend_disc', 'Discovery', shape='box', style='rounded,filled',
                       fillcolor=self.tactic_colors.get('discovery', '#E0E0E0'))
            legend.node('legend_exfil', 'Exfiltration', shape='box', style='rounded,filled',
                       fillcolor=self.tactic_colors.get('exfiltration', '#E0E0E0'))

        # Save
        output_path = f"{output_dir}/execution_order"
        dot.render(output_path, format='svg', cleanup=True)
        dot.render(output_path, format='png', cleanup=True)
        print(f"    [OK] Saved: execution_order.svg/png")

    def _visualize_dependencies(self, abilities: List[Dict], output_dir: str):
        """Visualize ability dependencies (payload/cleanup relationships)"""
        print("  [Creating dependency graph...]")

        # Create graph
        dot = Digraph(comment='Ability Dependencies')
        dot.attr(rankdir='LR')
        dot.attr('node', fontname='Malgun Gothic', fontsize='9', margin='0.2,0.1')
        dot.attr('edge', arrowsize='0.6')
        dot.attr(nodesep='0.4', ranksep='1.0')

        dot.attr(label='Ability Dependencies (Payloads & Cleanup)',
                fontsize='14', fontname='Malgun Gothic', labelloc='t')

        # Analyze dependencies
        has_dependencies = False

        for ability in abilities:
            ability_id = ability.get('ability_id')
            name = ability.get('name', 'Unknown')
            executors = ability.get('executors', [])

            if not executors:
                continue

            executor = executors[0]
            payloads = executor.get('payloads', [])
            cleanup = executor.get('cleanup', [])

            # Node style
            tactic = ability.get('tactic', 'unknown')
            color = self.tactic_colors.get(tactic, '#E0E0E0')

            # Add node if has dependencies
            if payloads or cleanup:
                has_dependencies = True
                short_id = ability_id[:8]
                label = f"{name}\\n({short_id})"
                dot.node(ability_id, label, shape='box', style='rounded,filled',
                        fillcolor=color)

                # Add payload nodes
                for payload in payloads:
                    payload_node = f"payload_{payload}"
                    dot.node(payload_node, payload, shape='note', style='filled',
                            fillcolor='#FFF9C4')
                    dot.edge(payload_node, ability_id, label='requires', fontsize='8')

                # Add cleanup nodes
                for cleanup_cmd in cleanup:
                    # Use first few words as identifier
                    cleanup_id = f"cleanup_{ability_id}_{hash(cleanup_cmd) % 1000}"
                    cleanup_label = cleanup_cmd[:30] + '...' if len(cleanup_cmd) > 30 else cleanup_cmd
                    dot.node(cleanup_id, cleanup_label, shape='oval', style='filled,dashed',
                            fillcolor='#FFECB3')
                    dot.edge(ability_id, cleanup_id, label='cleanup', fontsize='8',
                            style='dashed', color='#999999')

        if not has_dependencies:
            print("    [INFO] No payload/cleanup dependencies found")
            return

        # Save
        output_path = f"{output_dir}/dependencies"
        dot.render(output_path, format='svg', cleanup=True)
        dot.render(output_path, format='png', cleanup=True)
        print(f"    [OK] Saved: dependencies.svg/png")

    def _visualize_tactic_flow(self, abilities: List[Dict], adversary: Dict, output_dir: str):
        """Visualize kill chain tactic flow"""
        print("  [Creating tactic flow graph...]")

        atomic_ordering = adversary.get('atomic_ordering', [])
        ability_lookup = {a['ability_id']: a for a in abilities}

        # Extract tactic sequence
        tactic_sequence = []
        for ability_id in atomic_ordering:
            ability = ability_lookup.get(ability_id)
            if ability:
                tactic = ability.get('tactic', 'unknown')
                tactic_sequence.append(tactic)

        # Create graph
        dot = Digraph(comment='Tactic Flow')
        dot.attr(rankdir='LR')
        dot.attr('node', fontname='Malgun Gothic', fontsize='11', margin='0.4,0.3')
        dot.attr('edge', color='#666666', arrowsize='1.0', penwidth='2.0')
        dot.attr(nodesep='1.0', ranksep='1.5')

        dot.attr(label='Kill Chain: Tactic Flow',
                fontsize='14', fontname='Malgun Gothic', labelloc='t')

        # Group by tactic and count
        tactic_counts = {}
        prev_tactic = None
        tactic_transitions = []

        for tactic in tactic_sequence:
            tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1
            if prev_tactic and prev_tactic != tactic:
                tactic_transitions.append((prev_tactic, tactic))
            prev_tactic = tactic

        # Add nodes
        for tactic, count in tactic_counts.items():
            color = self.tactic_colors.get(tactic, '#E0E0E0')
            label = f"{tactic.upper()}\\n({count} abilities)"
            dot.node(tactic, label, shape='box', style='rounded,filled',
                    fillcolor=color, penwidth='2.0')

        # Add edges (unique transitions)
        unique_transitions = list(set(tactic_transitions))
        for from_tactic, to_tactic in unique_transitions:
            dot.edge(from_tactic, to_tactic)

        # Save
        output_path = f"{output_dir}/tactic_flow"
        dot.render(output_path, format='svg', cleanup=True)
        dot.render(output_path, format='png', cleanup=True)
        print(f"    [OK] Saved: tactic_flow.svg/png")


def main():
    """Test runner"""
    if len(sys.argv) < 3:
        print("Usage: python module5_visualization.py <abilities.yml> <adversaries.yml> [output_dir]")
        sys.exit(1)

    abilities_file = sys.argv[1]
    adversaries_file = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "data/visualizations"

    visualizer = AbilityFlowVisualizer()
    visualizer.visualize_abilities(abilities_file, adversaries_file, output_dir)


if __name__ == "__main__":
    main()
