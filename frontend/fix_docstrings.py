import os
import re

files_to_fix = [
    'src/modules/analytics/components/ReportBuilder.tsx',
    'src/modules/analytics/hooks/useAnalyticsAPI.ts',
    'src/modules/analytics/index.ts',
    'src/modules/analytics/components/index.ts',
    'src/modules/analytics/pages/FinanceDashboard.tsx',
    'src/modules/analytics/pages/InventoryDashboard.tsx',
    'src/modules/analytics/pages/SalesDashboard.tsx',
    'src/modules/analytics/components/Charts.tsx',
    'src/modules/analytics/pages/ProductionDashboard.tsx',
    'src/modules/analytics/pages/AnalyticsPage.tsx',
    'src/modules/analytics/hooks/index.ts',
    'src/modules/analytics/pages/index.ts',
]

for filepath in files_to_fix:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Replace Python docstrings with TypeScript comments
        # Match """ ... """ pattern at start of file
        content = re.sub(r'^\s*"""(.+?)"""\s*\n', r'// \1\n', content, flags=re.MULTILINE)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✓ {filepath}')
    except Exception as e:
        print(f'✗ {filepath}: {e}')

print('\nAll files fixed')
