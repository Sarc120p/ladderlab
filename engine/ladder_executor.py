"""
LadderLab – Ladder Logic Evaluator.
Evaluates contact chains (series / parallel) and returns the power flow result.
Supports both simple AND rungs and OR‑of‑ANDs (mixed lists).
"""

from typing import Callable, Union, List, Dict


class LadderExecutor:
    """
    Evaluates a Ladder program represented as a list of rungs.
    Each rung contains contacts (series/parallel) and optionally a coil,
    a timer or a counter.
    """

    @staticmethod
    def evaluate_rungs(
        rungs: List[dict],
        read_tag: Callable[[str], bool],
        write_tag: Callable[[str, bool], None]
    ) -> None:
        """
        Evaluate all rungs of a Ladder program.

        Args:
            rungs: List of rung objects (each with 'contacts' and optionally 'coil').
            read_tag: Callable that returns the current value of a tag.
            write_tag: Callable that schedules a write to a tag.
        """
        for rung in rungs:
            power = LadderExecutor._evaluate_contacts(
                rung.get("contacts", []), read_tag
            )
            coil = rung.get("coil", "")
            if coil:
                write_tag(coil, power)

    # ------------------------------------------------------------------
    # Contact evaluation
    # ------------------------------------------------------------------
    @staticmethod
    def _evaluate_contacts(
        contacts: Union[Dict, List],
        read_tag: Callable[[str], bool]
    ) -> bool:
        """
        Evaluate a contact chain.

        Supported formats:
          - dict                     → single contact
          - list of dicts            → series (AND) of contacts
          - list of lists            → OR of ANDs (each inner list is a series branch)
          - mixed list (dicts + lists) → each element is ANDed in series,
            where a dict is a contact and a list is an OR branch.

        Returns:
            True if the contact chain is closed (power flows), False otherwise.
        """
        # Normalise single contact to a list
        if isinstance(contacts, dict):
            contacts = [contacts]

        if not isinstance(contacts, list):
            return False

        # All elements at the top level are ANDed.
        for element in contacts:
            if not LadderExecutor._eval_element(element, read_tag):
                return False
        return True

    @staticmethod
    def _eval_element(
        element: Union[Dict, List],
        read_tag: Callable[[str], bool]
    ) -> bool:
        """
        Evaluate a single element of a contact chain.
        - dict  → a contact (NO/NC)
        - list  → an OR branch (at least one contact must be true)
        """
        if isinstance(element, dict):
            return LadderExecutor._eval_contact(element, read_tag)
        if isinstance(element, list):
            # OR branch: return True if any contact in the branch is closed
            return any(
                LadderExecutor._eval_contact(contact, read_tag)
                for contact in element
                if isinstance(contact, dict)
            )
        # Unknown element types are ignored (open circuit)
        return False

    @staticmethod
    def _eval_contact(
        contact: Dict,
        read_tag: Callable[[str], bool]
    ) -> bool:
        """Evaluate a single contact (NO or NC)."""
        tag = contact.get("tag", "")
        contact_type = contact.get("type", "NO")
        value = read_tag(tag)

        if contact_type == "NO":
            return value
        if contact_type == "NC":
            return not value

        # Unknown contact type – treat as open
        return False