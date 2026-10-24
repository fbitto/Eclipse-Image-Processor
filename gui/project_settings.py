"""Capture raw UI ticks, including hidden/advanced controls and ACHF panels."""
from PySide6.QtWidgets import QCheckBox,QComboBox,QSlider
from .components import CollapsibleSection


def controls(window):
    result={}
    def visit(key,value):
        if isinstance(value,(QSlider,QCheckBox,QComboBox)):
            result[key]=value
        elif isinstance(value,(list,tuple)):
            for index,item in enumerate(value):visit(f'{key}.{index}',item)
        elif isinstance(value,dict):
            for name,item in value.items():visit(f'{key}.{name}',item)
    for name,value in vars(window).items():
        if name.startswith(('sl_','chk_','combo_','achf_ael_controls')):
            visit(name,value)
    return result


def capture_settings(window):
    values={}
    for name,widget in controls(window).items():
        if isinstance(widget,QSlider):values[name]=dict(kind='slider',value=widget.value())
        elif isinstance(widget,QCheckBox):values[name]=dict(kind='check',value=widget.isChecked())
        else:values[name]=dict(kind='combo',value=widget.currentIndex(),text=widget.currentText())
    sections={name:dict(active=widget.is_filter_active(),expanded=widget.is_expanded)
        for name,widget in vars(window).items() if isinstance(widget,CollapsibleSection)}
    return dict(controls=values,sections=sections,
                geometry={key:getattr(window,'txt_'+key).text() for key in ('x','y','r')},
                auto_calculate=window.auto_calculate)


def validate_settings(window,settings):
    widgets=controls(window)
    values=settings.get('controls')
    if not isinstance(values,dict) or set(values)-{'chk_export_achf_ael'}!=set(widgets):
        raise ValueError('Settings controls do not match this application version')
    for name,record in values.items():
        if name=='chk_export_achf_ael':continue
        if not isinstance(record,dict):raise ValueError(f'Invalid control: {name}')
        widget=widgets[name];value=record.get('value')
        kind='slider' if isinstance(widget,QSlider) else 'check' if isinstance(widget,QCheckBox) else 'combo'
        expected=bool if kind=='check' else int
        if record.get('kind')!=kind or type(value) is not expected:
            raise ValueError(f'Invalid control value: {name}')
        if kind=='combo' and (not 0<=value<widget.count() or widget.itemText(value)!=record.get('text')):
            raise ValueError(f'Unknown selector value: {name}')
        if kind=='slider' and not -10**9<=value<=10**9:
            raise ValueError(f'Invalid slider value: {name}')
    geometry=settings.get('geometry',{})
    try:
        coords=[int(geometry[key]) for key in ('x','y','r')]
    except (KeyError,ValueError,TypeError):raise ValueError('Invalid saved disk geometry')
    if coords[2]<=0:raise ValueError('Saved disk radius must be positive')
    if type(settings.get('auto_calculate')) is not bool:raise ValueError('Invalid automatic calculation mode')
    sections=settings.get('sections')
    expected={n for n,w in vars(window).items() if isinstance(w,CollapsibleSection)}
    if not isinstance(sections,dict) or set(sections)!=expected:raise ValueError('Invalid saved filter sections')
    for record in sections.values():
        if not isinstance(record,dict) or any(type(record.get(k)) is not bool for k in ('active','expanded')):
            raise ValueError('Invalid saved filter activation')


def restore_settings(window,settings):
    validate_settings(window,settings)
    widgets=controls(window)
    # Older JSON files contain the removed all-ACHF export checkbox.
    values={name:record for name,record in settings['controls'].items()
            if name!='chk_export_achf_ael'}
    previous=window.auto_calculate
    window.auto_calculate=False
    try:
        for key,value in settings['geometry'].items():getattr(window,'txt_'+key).setText(value)
        # Selector callbacks establish slider ranges and variant-panel visibility.
        for name,record in values.items():
            if record['kind']=='combo':widgets[name].setCurrentIndex(record['value'])
        # Two passes accommodate linked GHS SP/LP/HP/BP/WP bounds.
        for _ in range(2):
            for name,record in values.items():
                if record['kind']=='slider':
                    widget=widgets[name]
                    if name=='sl_fnrgf_rmax' or name.startswith('sl_mgn_sigmas.'):widget.setMaximum(max(widget.maximum(),record['value']))
                    widget.setValue(record['value'])
        for name,record in values.items():
            if record['kind']=='check':widgets[name].setChecked(record['value'])
        for name,record in settings['sections'].items():
            section=getattr(window,name)
            if section.chk_active is not None:section.chk_active.setChecked(record['active'])
            if section.is_expanded!=record['expanded']:section.toggle_expanded()
        for name,record in values.items():
            if record['kind']=='slider' and widgets[name].value()!=record['value']:
                raise ValueError(f'Saved value is outside the supported range: {name}')
        window.auto_calculate=settings['auto_calculate']
        window.btn_auto_calc.setChecked(window.auto_calculate)
        window.btn_auto_calc.setText('Auto Calculate' if window.auto_calculate else 'Man Calc')
        window.btn_recalc.setVisible(not window.auto_calculate)
    except Exception:
        window.auto_calculate=previous
        raise
    finally:
        window.recalculation_timer.stop()
        window.presentation_timer.stop()
