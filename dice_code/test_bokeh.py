from bokeh.io import vform
from bokeh.models import HoverTool, CustomJS
from bokeh.models.widgets import TextInput
from bokeh.plotting import output_file, figure, show, ColumnDataSource

output_file("plot.html")

words = ["werner", "herbert", "klaus"]
x, y = [1,2,3], [1,2,3]
color = ['green', 'blue', 'red']

source = ColumnDataSource(data=dict(x=x, y=y, words=words, color=color))

hover = HoverTool(tooltips=[("word", "@words")])

p = figure(plot_height=600, plot_width=800, title="word2vec", tools=[hover])
p.circle('x','y', radius=0.1, fill_color='color', source=source, line_color=None)

callback = CustomJS(args=dict(source=source), code="""
    console.log(source);
    var data = source.get('data')
    console.log(data);
    var value = cb_obj.get('value')
    var words = data['words']
    for (i=0; i < words.length; i++) {
        if ( words[i]==value ) { data.color[i]='yellow' }
    }
    source.trigger('change')
""")

word_input = TextInput(value="word", title="Point out a word", callback=callback)

layout = vform(word_input, p)

show(layout)
