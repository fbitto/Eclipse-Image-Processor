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



def filter_widgets(window):
    from core.layer_engine import ORDER
    sections=[getattr(window,'sec_'+name) for name in (*ORDER,'achf')]
    return {name:widget for name,widget in controls(window).items()
            if any(section.isAncestorOf(widget) for section in sections)}


def initialize_filter_defaults(window):
    """Capture factory parameters once, with the requested AEL composition and 25/75 alternatives."""
    from core.layer_engine import ORDER
    settings=capture_settings(window)
    names=filter_widgets(window)
    values={name:record for name,record in settings['controls'].items() if name in names}
    for name in ORDER+('achf',):
        values['sl_'+name+'_str']['value']=25
        values['sl_'+name+'_opacity']['value']=75
    for variant in window.achf_ael_controls:
        values[f'achf_ael_controls.{variant}.strength']['value']=25
        values[f'achf_ael_controls.{variant}.opacity']['value']=75
        values[f'achf_ael_controls.{variant}.enabled']['value']=False
    values['chk_achf_adaptive']['value']=False
    for name,opacity in (('nrgf',40),('wow',35)):
        values['sl_'+name+'_str']['value']=100
        values['sl_'+name+'_opacity']['value']=opacity
    for variant in ('ael_iso_04','ael_angular_4'):
        values[f'achf_ael_controls.{variant}.strength']['value']=100
        values[f'achf_ael_controls.{variant}.opacity']['value']=10
    values['sl_wow_scales']['value']=6
    values['sl_wow_noise_floor']['value']=30
    for name,index in (('combo_wow_bilateral',2),('combo_achf_variant',2)):
        values[name]=dict(kind='combo',value=index,text=names[name].itemText(index))
    window._filter_defaults=values
    for name,record in values.items():
        if record['kind']=='slider':names[name].setProperty('reset_value',record['value'])
    reset_filter_defaults(window,ael=False)


def reset_filter_defaults(window, *, ael=False):
    """Never carry filter edits or inclusion flags from the preceding image/project."""
    from core.layer_engine import ORDER
    widgets=filter_widgets(window)
    previous=window.auto_calculate
    window.auto_calculate=False
    try:
        values=window._filter_defaults
        for name,record in values.items():
            if record['kind']=='combo':widgets[name].setCurrentIndex(record['value'])
        for _ in range(2):
            for name,record in values.items():
                if record['kind']=='slider':
                    widget=widgets[name]
                    if name=='sl_fnrgf_rmax' or name.startswith('sl_mgn_sigmas.'):
                        widget.setMaximum(max(widget.maximum(),record['value']))
                    widget.setValue(record['value'])
        for name,record in values.items():
            if record['kind']=='check':widgets[name].setChecked(record['value'])
        for variant in ('ael_iso_04','ael_angular_4'):
            window.achf_ael_controls[variant]['enabled'].setChecked(ael)
        for name in ORDER+('achf',):
            section=getattr(window,'sec_'+name)
            section.chk_active.setChecked(ael and name in ('fnrgf','mgn','wow','achf'))
        window.update_wow_controls()
    finally:
        window.auto_calculate=previous
        window.recalculation_timer.stop()
        window.presentation_timer.stop()


def validate_settings(window,settings):
    widgets=controls(window)
    values=settings.get('controls')
    optional=set(filter_widgets(window)) | {'chk_color_correction'}
    if (not isinstance(values,dict) or set(values)-set(widgets)-{'chk_export_achf_ael'} or
            set(widgets)-set(values)-optional):
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
    optional_sections={name for name in expected if name not in ('sec_geo','sec_stretch')}
    if (not isinstance(sections,dict) or set(sections)-expected or expected-set(sections)-optional_sections):
        raise ValueError('Invalid saved filter sections')
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
        reset_filter_defaults(window,ael=False)
        window.chk_color_correction.setChecked(False)
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
