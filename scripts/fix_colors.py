with open('C:/Users/hp/Downloads/yeabsiragebre/scripts/generate_stats.py', 'r') as f:
    c = f.read()

c = c.replace('CYAN = "#36E0C0"', 'ORANGE = "#FFA500"')
c = c.replace('CYAN_2 = "#63B3FF"', 'ORANGE_2 = "#FFB347"')
c = c.replace('CYAN', 'ORANGE')
c = c.replace('ORANGE_2 = "#FFA500"', 'ORANGE_2 = "#FFB347"')

with open('C:/Users/hp/Downloads/yeabsiragebre/scripts/generate_stats.py', 'w') as f:
    f.write(c)
print('Done')