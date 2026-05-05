import matplotlib.pyplot as plt

# 1. Define the data 
time_periods = ['2006-2010', '2010-2016', '2016-2020', '2006-2020']

data = {
    'Bare area': {'values': [0, 0, 2, 7], 'color': '#1f3b73'},
    'Forest': {'values': [-1, -2, -1, -4], 'color': '#00b050'},
    'Grassland': {'values': [1, 2, -3, -11], 'color': '#c49000'},
    'Built-up area': {'values': [1, -20, 1, -14], 'color': '#ff0000'},
    'Irrigated cropland': {'values': [-10, 71, 12, 126], 'color': '#ffc000'},
    'Others': {'values': [0, 12, 3, 25], 'color': '#a6a6a6'},
    'Rainfed cropland': {'values': [7, 6, 2, 17], 'color': '#ffff00'},
    'Shrubland': {'values': [8, 4, 1, 15], 'color': '#6b723f'},
    'Water bodies': {'values': [-1, 26, 27, 160], 'color': '#00b0f0'}
}

# 2. Set up the plot with a high-resolution figure size
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

# 3. Plot each line
for label, properties in data.items():
    ax.plot(time_periods, properties['values'], marker='o', markersize=4, 
            linewidth=1.5, label=label, color=properties['color'])

# 4. Add the zero baseline
ax.axhline(0, color='black', linewidth=1)

# 5. Formatting axes and labels
ax.set_ylabel('Percentage change (%)', fontsize=11, color='#555555')
ax.set_xlabel('Time Periods', fontsize=11, color='#555555')

# Set y-axis limits and ticks to match the original chart
ax.set_ylim(-25, 175)
ax.set_yticks(range(-25, 176, 25))

# Style the ticks
ax.tick_params(axis='x', colors='#555555')
ax.tick_params(axis='y', colors='#555555')

# Remove top and right spines for a cleaner look
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(1.5)
ax.spines['bottom'].set_linewidth(1.5)

# 6. Add the legend outside the plot area
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False, 
           handlelength=2, labelcolor='#555555')

# Adjust layout to fit the legend 
plt.tight_layout()

# 7. Save the chart in high resolution (300 DPI)
plt.savefig('high_res_land_cover_chart.png', dpi=300, bbox_inches='tight')

# Show the plot
plt.show()