import os
import re
import unittest

class HardcodingAuditTest(unittest.TestCase):
    """
    Automated test to detect potential hard-coded strings in critical logic files.
    Ensures that dynamic configuration (get_config) is preferred over literal strings.
    """
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TARGET_FILES = [
        os.path.join(BASE_DIR, "groq_client.py"),
        os.path.join(BASE_DIR, "views.py"),
    ]
    
    # Keywords that SHOULD NOT be used as literals without get_config
    SENSITIVE_KEYWORDS = [
        "palette_primary", "palette_secondary", "palette_accent",
        "cta_headline", "contact_description", "toc_title",
        "master_prompt_template", "format_rules", "ai_model_name",
        "job_msg_", "job_err_"
    ]

    def test_get_config_usage(self):
        """Verify that sensitive keywords are always wrapped in get_config() calls."""
        for file_path in self.TARGET_FILES:
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for kw in self.SENSITIVE_KEYWORDS:
                    if kw in line:
                        # If it's a assignment key, we check if the value side has get_config
                        if f'"{kw}"' in line or f"'{kw}'" in line:
                            # If it's being used as a key, check if get_config is also on this line
                            # or if it's a legitimate dictionary access
                            if "get_config" not in line and "=" in line and line.find("=") < line.find(kw):
                                # This might be an assignment with a hardcoded value
                                # but wait, if it's 'get_config(kw)', it's fine.
                                pass
                            
                            # Real check: if the keyword is used as a string literal, 
                            # it must be inside get_config()
                            if f'get_config("{kw}"' in line or f"get_config('{kw}'" in line:
                                continue
                            
                            # If it's a key in a dictionary being assigned, it's fine as long as 
                            # there is a get_config on the right side OR it's a fallback logic
                            if "normalized[" in line or "vars[" in line or "template_vars[" in line:
                                if "get_config" in line:
                                    continue

                            # If it's just a variable name or part of a larger string, ignore
                            if f'"{kw}"' not in line and f"'{kw}'" not in line:
                                continue

                            self.fail(f"Potential hard-coded reference to '{kw}' found in {os.path.basename(file_path)}:L{line_num}\nLine: {line.strip()}")

    def test_no_raw_hex_colors_in_logic(self):
        """Detect raw hex colors in Python logic (should be in constants or DB)."""
        hex_pattern = re.compile(r'#[A-Fa-f0-9]{6}\b')
        
        for file_path in self.TARGET_FILES:
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            matches = hex_pattern.finditer(content)
            for match in matches:
                # Get context around the match (100 chars before)
                start_idx = max(0, match.start() - 200)
                context = content[start_idx:match.end()]
                
                # Hex colors are allowed if they are default values in get_config() or in constants.py
                if "get_config" in context or "DEFAULT_" in context or "_TYPE_MAP" in context or "palette_dark_mode" in context:
                    continue
                
                # Get line number
                line_num = content.count('\n', 0, match.start()) + 1
                line = content.splitlines()[line_num-1]
                
                self.fail(f"Raw hex color '{match.group(0)}' found in {os.path.basename(file_path)}:L{line_num} outside of get_config() or constants.\nLine: {line.strip()}")

    def test_template_dynamic_labels(self):
        """Ensure Template.html uses variables for labels and page numbers."""
        template_path = os.path.join(self.BASE_DIR, "templates", "Template.html")
        if not os.path.exists(template_path):
            return
            
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check for hard-coded page numbers in header
        page_num_pattern = re.compile(r'<div class="page-number-enhanced">\d+</div>')
        matches = page_num_pattern.findall(content)
        self.assertEqual(len(matches), 0, f"Found hard-coded page numbers in Template.html: {matches}")
        
        # Check for "Strategic Tip" literal
        self.assertNotIn("Strategic Tip", content, "Found hard-coded 'Strategic Tip' in Template.html. Use {{strategicTipLabel}} instead.")

if __name__ == "__main__":
    unittest.main()
