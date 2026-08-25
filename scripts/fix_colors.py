with open("C:/Users/hp/Downloads/yeabsiragebre/scripts/generate_stats.py", "r") as f:
    c = f.read()

# Rename the accent color variables to GOLD, keeping the general->specific order
# so we don't accidentally clobber CYAN_2 while replacing CYAN.
c = c.replace('CYAN_2 = "#63B3FF"', 'GOLD_2 = "#F1C453"')
c = c.replace('CYAN = "#36E0C0"', 'GOLD = "#D4AF37"')

# Catch any remaining bare references to the old names used elsewhere in the file
c = c.replace("CYAN_2", "GOLD_2")
c = c.replace("CYAN", "GOLD")

with open("C:/Users/hp/Downloads/yeabsiragebre/scripts/generate_stats.py", "w") as f:
    f.write(c)

print("Done")
