"""Capture raw UI ticks, including hidden/advanced controls and ACHF panels."""
import math
from copy import deepcopy
from PySide6.QtWidgets import QAbstractButton,QComboBox,QSlider
from .components import CollapsibleSection


def controls(window):
    result={}
    def visit(key,value):
        if isinstance(value,(QSlider,QAbstractButton,QComboBox)):
            result[key]=value
        elif isinstance(value,(list,tuple)):
            for index,item in enumerate(value):visit(f'{key}.{index}',item)
        elif isinstance(value,dict):
            for name,item in value.items():visit(f'{key}.{name}',item)
    for name,value in vars(window).items():
        if name.startswith(('sl_','chk_','combo_','achf_ael_controls')) or name == 'btn_psb_preview':
            visit(name,value)
    return result


def capture_settings(window):
    values={}
    for name,widget in controls(window).items():
        if isinstance(widget,QSlider):values[name]=dict(kind='slider',value=widget.value())
        elif isinstance(widget,QAbstractButton):values[name]=dict(kind='check',value=widget.isChecked())
        else:values[name]=dict(kind='combo',value=widget.currentIndex(),text=widget.currentText())
    sections={name:dict(active=widget.is_filter_active(),expanded=widget.is_expanded)
        for name,widget in vars(window).items() if isinstance(widget,CollapsibleSection)}
    return dict(background_samples=([list(p) for p in window.background.points] if window.background.points is not None else None),controls=values,sections=sections,
                geometry={key:getattr(window,'txt_'+key).text() for key in ('x','y','r')},
                auto_calculate=window.auto_calculate,ui_mode=window.ui_level.currentData())



def filter_widgets(window):
    from core.layer_engine import ORDER
    sections=[getattr(window,'sec_'+name) for name in (*ORDER,'achf')]
    sections += list(getattr(window,'achf_cards',{}).values())
    return {name:widget for name,widget in controls(window).items()
            if any(section.isAncestorOf(widget) for section in sections)}


def initialize_filter_defaults(window):
    """Capture opacity-only defaults; Linear Light keeps its independent Gain."""
    from core.layer_engine import ORDER
    settings=capture_settings(window)
    names=filter_widgets(window)
    values={name:record for name,record in settings['controls'].items() if name in names}
    for name in ORDER+('achf',):
        values['sl_'+name+'_opacity']['value']=75 if name == 'larson_sekanina' else 19 if name == 'achf' else 20
    values['sl_larson_sekanina_str']['value']=25
    for variant in window.achf_ael_controls:
        values[f'achf_ael_controls.{variant}.opacity']['value']=10
        values[f'achf_ael_controls.{variant}.enabled']['value']=False
    values['chk_achf_adaptive']['value']=False
    for name,opacity in (('nrgf',40),('wow',10)):
        values['sl_'+name+'_opacity']['value']=opacity
    values['sl_wow_scales']['value']=8
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


def _normalized_settings(window,settings):
    """Import current v4 recipes without reinterpreting selector indices."""
    if not isinstance(settings,dict):return settings
    result=deepcopy(settings)
    values=result.get('controls',{})
    if not isinstance(values,dict):return result
    old=values.get('combo_input_state')
    if isinstance(old,dict):
        mapping={(0,'Input: linearity unspecified'):'linear',(1,'Input: linear'):'linear',
                 (2,'Input: already stretched / nonlinear'):'nonlinear'}
        state=(mapping.get((old.get('value'),old.get('text')))
               if type(old.get('value')) is int and isinstance(old.get('text'),str) else None)
        if state is not None:
            index=window.combo_input_state.findData(state)
            values['combo_input_state']=dict(kind=old.get('kind'),value=index,
                                             text=window.combo_input_state.itemText(index))
    if 'ui_mode' not in result:
        advanced=values.get('chk_advanced',{})
        result['ui_mode']='expert' if isinstance(advanced,dict) and advanced.get('value') is True else 'standard'
    sections=result.get('sections',{})
    if isinstance(sections,dict) and isinstance(sections.get('sec_achf'),dict) and sections['sec_achf'].get('active') is False:
        # Old include flags under a disabled parent were not active filters.
        for name,record in values.items():
            if name=='chk_achf_adaptive' or (name.startswith('achf_ael_controls.') and name.endswith('.enabled')):
                if isinstance(record,dict) and record.get('kind')=='check' and type(record.get('value')) is bool:
                    record['value']=False
        for name,record in sections.items():
            if name.startswith('sec_achf_') and isinstance(record,dict) and type(record.get('active')) is bool:
                record['active']=False
    return result


def validate_settings(window,settings):
    settings=_normalized_settings(window,settings)
    if not isinstance(settings,dict) or set(settings) != {'background_samples','controls','sections','geometry','auto_calculate','ui_mode'}:
        raise ValueError('Settings do not match the current format')
    if settings['ui_mode'] not in ('basic','standard','expert'):
        raise ValueError('Unknown interface level')
    widgets=controls(window)
    values=settings.get('controls')
    if isinstance(values,dict):
        values={k:v for k,v in values.items() if k != 'sl_achf_background'}
    optional=set(filter_widgets(window)) | {'chk_statistics_separate_ael','btn_psb_preview','chk_prominences','sl_prominence_exposure','combo_background_degree','sl_warmth','sl_prominence_saturation','sl_prominence_contrast','sl_prominence_edge_softness'}
    if (not isinstance(values,dict) or set(values)-set(widgets) or
            set(widgets)-set(values)-optional):
        raise ValueError('Settings controls do not match this application version')
    for name,record in values.items():
        if not isinstance(record,dict):raise ValueError(f'Invalid control: {name}')
        widget=widgets[name];value=record.get('value')
        kind='slider' if isinstance(widget,QSlider) else 'check' if isinstance(widget,QAbstractButton) else 'combo'
        expected=bool if kind=='check' else int
        if record.get('kind')!=kind or type(value) is not expected:
            raise ValueError(f'Invalid control value: {name}')
        legacy_wow = name=='combo_wow_bilateral' and record.get('text') in {
            0: ('Standard WOW',), 1: ('Edge-aware WOW (adjustable bilateral)',),
            2: ('AEL bilateral',)}.get(value, ())
        if kind=='combo' and (not 0<=value<widget.count() or (widget.itemText(value)!=record.get('text') and not legacy_wow)):
            raise ValueError(f'Unknown selector value: {name}')
        if kind=='slider' and not -10**9<=value<=10**9:
            raise ValueError(f'Invalid slider value: {name}')
    geometry=settings.get('geometry',{})
    try:
        coords=[float(geometry[key]) for key in ('x','y','r')]
    except (KeyError,ValueError,TypeError):raise ValueError('Invalid saved disk geometry')
    if not all(math.isfinite(v) for v in coords) or coords[2]<=0:raise ValueError('Saved disk radius must be positive')
    if type(settings.get('auto_calculate')) is not bool:raise ValueError('Invalid automatic calculation mode')
    points=settings.get('background_samples')
    if points is not None:
        if (not isinstance(points,(list,tuple)) or len(points)>5000 or any(
                not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(v) is not int or v<0 or v>10**9 for v in p)
                for p in points)):
            raise ValueError('Invalid background sample coordinates')
    sections=settings.get('sections')
    expected={n for n,w in vars(window).items() if isinstance(w,CollapsibleSection)}
    optional_sections={name for name in expected if name != 'sec_geo'}
    if (not isinstance(sections,dict) or set(sections)-expected or expected-set(sections)-optional_sections):
        raise ValueError('Invalid saved filter sections')
    for record in sections.values():
        if not isinstance(record,dict) or any(type(record.get(k)) is not bool for k in ('active','expanded')):
            raise ValueError('Invalid saved filter activation')


def restore_settings(window,settings, *, source_shape=None):
    """Apply a recipe atomically, including ranges changed by selector callbacks."""
    settings=_normalized_settings(window,settings)
    validate_settings(window,settings)
    previous=capture_settings(window)
    ranges={name:(widget.minimum(),widget.maximum()) for name,widget in controls(window).items()
            if isinstance(widget,QSlider)}
    window._restoring_settings=True
    previous_shape=window.full_raw_image.shape if window.full_raw_image is not None else (5120,5120)
    window._restoring_source_shape=source_shape if source_shape is not None else previous_shape
    try:
        _apply_settings(window,settings)
    except Exception:
        window._restoring_source_shape=previous_shape
        _apply_settings(window,previous)
        for name,(minimum,maximum) in ranges.items():
            controls(window)[name].setRange(minimum,maximum)
        raise
    finally:
        del window._restoring_source_shape
        window._restoring_settings=False
        window.recalculation_timer.stop()
        window.presentation_timer.stop()


def _apply_settings(window,settings):
    widgets=controls(window)
    values={k:v for k,v in settings['controls'].items() if k != 'sl_achf_background'}
    previous=window.auto_calculate
    window.auto_calculate=False
    try:
        reset_filter_defaults(window,ael=False)
        window.combo_background_degree.setCurrentIndex(0)
        window.btn_psb_preview.setChecked(True)
        window.chk_statistics_separate_ael.setChecked(False)
        window.prominence_view.setCurrentIndex(0)
        window.chk_prominences.setChecked(False)
        window.sl_prominence_exposure.setValue(-200)
        window.sl_prominence_saturation.setValue(65)
        window.sl_prominence_contrast.setValue(20)
        window.sl_prominence_edge_softness.setValue(30)
        window.sl_warmth.setValue(0)
        window.background.points=([tuple(p) for p in settings['background_samples']] if settings.get('background_samples') is not None else None)
        window.background.dirty=window.background.base is not None
        for key,value in settings['geometry'].items():getattr(window,'txt_'+key).setText(value)
        # Selector callbacks establish slider ranges and variant-panel visibility.
        for name,record in values.items():
            if record['kind']=='combo':widgets[name].setCurrentIndex(record['value'])
        # Resolve linked filter bounds after the selectors and geometry.
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
            # ACHF inclusion is canonical in controls; cards persist expansion only.
            if section.chk_active is not None and section not in window.achf_cards.values():
                section.chk_active.setChecked(record['active'])
            if section.is_expanded!=record['expanded']:section.toggle_expanded()
        for name,record in values.items():
            if record['kind']=='slider' and widgets[name].value()!=record['value']:
                raise ValueError(f'Saved value is outside the supported range: {name}')
        from PySide6.QtCore import QSignalBlocker
        from .ui_levels import sync_achf_master
        sync_achf_master(window)
        with QSignalBlocker(window.ui_level):
            window.ui_level.setCurrentIndex(window.ui_level.findData(settings['ui_mode']))
        window.apply_ui_level(recalculate=False)
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
