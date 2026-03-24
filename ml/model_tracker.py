"""
CitiZen AI — Model Tracker & Accuracy Visualization
Plotly charts for model performance, category distribution, urgency breakdown.
"""
import plotly.graph_objects as go
import pandas as pd


def get_accuracy_chart():
    """Return Plotly figure showing model accuracy over versions."""
    try:
        from utils.data_utils import get_model_versions
        versions = get_model_versions()
    except Exception:
        versions = []

    if len(versions) < 1:
        versions = [
            {"version_num": 1, "accuracy": 0.74, "trained_at": "Initial"},
        ]

    fig = go.Figure()

    # Area fill
    fig.add_trace(go.Scatter(
        x=[f"v{v['version_num']}" for v in versions],
        y=[v['accuracy'] * 100 for v in versions],
        fill='tozeroy',
        fillcolor='rgba(0,212,255,0.08)',
        line=dict(color='#00D4FF', width=2),
        mode='lines+markers',
        marker=dict(size=8, color='#7C3AED',
                    line=dict(width=2, color='#00D4FF')),
        name='Accuracy %',
        hovertemplate='<b>%{x}</b><br>Accuracy: %{y:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Model Version',
                   title_font=dict(color='#8B98B8')),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Accuracy (%)',
                   range=[0, 100], title_font=dict(color='#8B98B8')),
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text='Model Accuracy — Improving with Corrections',
                   font=dict(color='#F0F4FF', size=14, family='Sora')),
        showlegend=False,
        height=280
    )
    return fig


def get_category_distribution_chart(stats_by_category=None):
    """Complaints by category — horizontal bar."""
    if stats_by_category is None or len(stats_by_category) == 0:
        stats_by_category = [
            {"category": "Roads & Potholes", "count": 0},
            {"category": "Garbage & Waste Management", "count": 0},
        ]

    df = pd.DataFrame(stats_by_category)

    fig = go.Figure(go.Bar(
        y=df['category'],
        x=df['count'],
        orientation='h',
        marker=dict(
            color=df['count'],
            colorscale=[[0, '#7C3AED'], [1, '#00D4FF']],
            showscale=False
        ),
        hovertemplate='%{y}: %{x} complaints<extra></extra>'
    ))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)',
                   autorange='reversed'),
        margin=dict(l=0, r=0, t=10, b=0),
        height=260
    )
    return fig


def get_urgency_donut(high, medium, low):
    """Urgency distribution donut chart."""
    total = high + medium + low
    if total == 0:
        high, medium, low = 1, 1, 1
        total = 3

    fig = go.Figure(go.Pie(
        values=[high, medium, low],
        labels=['High', 'Medium', 'Low'],
        hole=0.65,
        marker=dict(
            colors=['#FF4444', '#FFB800', '#39FF14'],
            line=dict(color='#0A0E1A', width=2)
        ),
        hovertemplate='%{label}: %{value}<extra></extra>',
        textinfo='none'
    ))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        showlegend=True,
        legend=dict(orientation='h', x=0.1, font=dict(color='#8B98B8')),
        margin=dict(l=0, r=0, t=10, b=0),
        height=220,
        annotations=[dict(
            text=f'{high + medium + low}<br>total',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color='#F0F4FF', family='JetBrains Mono')
        )]
    )
    return fig


def get_daily_trend_chart(daily_data=None):
    """Daily complaint trend area chart."""
    if daily_data is None or len(daily_data) == 0:
        daily_data = [{"day": "2026-03-20", "count": 0}]

    df = pd.DataFrame(daily_data)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['day'],
        y=df['count'],
        fill='tozeroy',
        fillcolor='rgba(0,212,255,0.08)',
        line=dict(color='#00D4FF', width=2),
        mode='lines+markers',
        marker=dict(size=6, color='#00D4FF'),
        hovertemplate='%{x}<br>Complaints: %{y}<extra></extra>'
    ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Date',
                   title_font=dict(color='#8B98B8')),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Complaints',
                   title_font=dict(color='#8B98B8')),
        margin=dict(l=0, r=0, t=10, b=0),
        height=250,
        showlegend=False
    )
    return fig


def get_resolution_by_category_chart(complaints_data=None):
    """Resolution time by category box chart."""
    if complaints_data is None or len(complaints_data) == 0:
        return go.Figure()

    df = pd.DataFrame(complaints_data)

    # Calculate resolution hours for resolved complaints
    resolved = df[df['resolved_at'].notna() & df['created_at'].notna()].copy()
    if len(resolved) == 0:
        return go.Figure()

    try:
        resolved['created_at'] = pd.to_datetime(resolved['created_at'])
        resolved['resolved_at'] = pd.to_datetime(resolved['resolved_at'])
        resolved['hours'] = (resolved['resolved_at'] - resolved['created_at']).dt.total_seconds() / 3600
    except Exception:
        return go.Figure()

    categories = resolved['category'].unique()
    fig = go.Figure()

    colors = ['#00D4FF', '#7C3AED', '#39FF14', '#FFB800', '#FF4444',
              '#00D4FF', '#7C3AED', '#39FF14']

    for i, cat in enumerate(categories):
        cat_data = resolved[resolved['category'] == cat]
        fig.add_trace(go.Box(
            y=cat_data['hours'],
            name=cat[:15],
            marker_color=colors[i % len(colors)],
            line=dict(color=colors[i % len(colors)])
        ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Hours',
                   title_font=dict(color='#8B98B8')),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        margin=dict(l=0, r=0, t=10, b=0),
        height=260,
        showlegend=False
    )
    return fig


def get_agent_leaderboard_chart(agents_data=None):
    """Agent leaderboard bar chart."""
    if agents_data is None or len(agents_data) == 0:
        return go.Figure()

    df = pd.DataFrame(agents_data)
    df = df.sort_values('total_resolved', ascending=True)

    fig = go.Figure(go.Bar(
        y=df['name'],
        x=df['total_resolved'],
        orientation='h',
        marker=dict(
            color=df['total_resolved'],
            colorscale=[[0, '#7C3AED'], [1, '#39FF14']],
            showscale=False
        ),
        hovertemplate='%{y}: %{x} resolved<extra></extra>'
    ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#8B98B8'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Cases Resolved'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        margin=dict(l=0, r=0, t=10, b=0),
        height=260,
        showlegend=False
    )
    return fig
