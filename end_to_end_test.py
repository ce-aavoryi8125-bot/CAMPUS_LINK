# Compatibility shim forwarding to tests/end_to_end_test.py
import tests.end_to_end_test as eet

if __name__ == "__main__":
    eet.setup()
    eet.test_schema()
    eet.test_constraints()
    eet.test_crud()
    eet.test_alter()
    eet.test_queries()
    eet.test_availability()
    eet.test_workflow()
    eet.test_damage_workflow()
    eet.test_reports()
    eet.test_saves_wishlist()
    eet.test_trust_score()
    eet.print_summary()
