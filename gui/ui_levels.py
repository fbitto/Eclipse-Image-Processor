"""Interface levels and independent ACHF cards; numerical filter parameters stay canonical."""
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider

from .components import CollapsibleSection, ScrollSafeComboBox
from .filter_controls import set_control_visible


def build_achf_cards(window):
    """Move the existing controls into cards without duplicating their values."""
    parent = window.sec_achf.parentWidget().layout()
    window.achf_cards = {}
    entries = [('adaptive','ACHF Adaptive',window.achf_adaptive_panel,window.chk_achf_adaptive)]
    entries += [(variant,title,window.achf_ael_controls[variant]['panel'],
                 window.achf_ael_controls[variant]['enabled']) for variant,title in
                [('ael_iso_01','ACHF ISO 01'),('ael_iso_04','ACHF ISO 04'),('ael_angular_4','ACHF Angular')]]
    def activation_changed(_):
        if getattr(window,'_restoring_settings',False):return
        sync_achf_master(window)
        window.dispatch_pipeline_request_if_auto()
    for variant,title,panel,enabled in entries:
        card = CollapsibleSection(title,has_checkbox=False,is_expanded=False)
        description = ('Accepted opposite-neighbor pairs extract signed detail from the working input.' if variant == 'adaptive' else
                       'AEL log-luminance detail blended with Overlay; best used on linear input. Boundary bands can remain.')
        card.toggle_btn.setToolTip(description+' Expand or collapse this variant; expansion does not activate it.')
        card.content_layout.addWidget(panel)
        panel.setVisible(True);panel.setEnabled(True)
        enabled.toggled.disconnect()
        enabled.setText('Active')
        enabled.setAccessibleName(title+' active')
        enabled.setToolTip('Enable or bypass '+title+' independently. Retains parameters and cached results when disabled.')
        card.header_frame.layout().addWidget(enabled)
        card.has_checkbox=True;card.chk_active=enabled
        enabled.toggled.connect(card._on_active_toggled)
        enabled.toggled.connect(activation_changed)
        parent.addWidget(card)
        window.achf_cards[variant]=card
        setattr(window,'sec_achf_'+variant,card)
    window.sec_achf.hide()
    window.combo_achf_variant.hide()


def sync_achf_master(window):
    included = window.chk_achf_adaptive.isChecked() or any(
        controls['enabled'].isChecked() for controls in window.achf_ael_controls.values())
    with QSignalBlocker(window.sec_achf.chk_active):
        window.sec_achf.chk_active.setChecked(included)


def add_ui_levels(window, header_layout):
    row=QHBoxLayout()
    label=QLabel('Controls')
    label.setStyleSheet('QLabel { background: transparent; border: none; }')
    window.ui_level=ScrollSafeComboBox()
    window.ui_level.setAccessibleName('Controls level')
    label.setBuddy(window.ui_level)
    for title,value in [('Basic','basic'),('Standard','standard'),('Expert','expert')]:
        window.ui_level.addItem(title,value)
    window.ui_level.setCurrentIndex(0)
    window.ui_level.setToolTip('Basic starts the first directly opened image with NAFE, FNRGF, WOW, Tangential, ISO04 and Angular; NRGF and MGN are also available. Standard shows all filters with common controls; Expert adds numerical parameters and statistical exclusions. Switching levels preserves eligible settings and does not reapply the starter. Basic disables excluded filters.')
    label.setToolTip(window.ui_level.toolTip())
    row.addWidget(label);row.addWidget(window.ui_level,1)
    header_layout.insertLayout(1,row)
    window.ui_level_note=QLabel()
    window.ui_level_note.setWordWrap(True)
    window.ui_level_note.setStyleSheet('QLabel { color: #bbbbbb; background: transparent; border: none; }')
    window.ui_level_note.setToolTip('Changing to Basic disables excluded filters but retains their parameters. Returning to Standard or Expert does not enable them again.')
    header_layout.addWidget(window.ui_level_note)
    window.chk_advanced.hide()
    window.ui_level.currentIndexChanged.connect(lambda _: apply_ui_level(window))
    def legacy_expert(checked):
        if not getattr(window,'_restoring_settings',False):
            window.ui_level.setCurrentIndex(2 if checked else 1)
    window.chk_advanced.toggled.connect(legacy_expert)
    apply_ui_level(window)


def apply_ui_level(window, *, recalculate=True):
    """Batch Basic restrictions, then request at most one numerical update."""
    if not hasattr(window,'ui_level'):return
    from .project_settings import filter_widgets
    mode=window.ui_level.currentData()
    basic=mode=='basic';expert=mode=='expert'
    window.filter_settings_layout.parentWidget().parentWidget().setVisible(not basic)
    window.combo_normalization_mode.setVisible(not basic)
    widgets=filter_widgets(window)
    # Restore the shared controls before applying each level's visibility rules.
    for widget in widgets.values():
        if isinstance(widget,QSlider):set_control_visible(widget,True)
        elif widget is not window.combo_achf_variant:widget.setVisible(True)
    with QSignalBlocker(window.chk_advanced):window.chk_advanced.setChecked(expert)
    window.update_detail_visibility(expert)
    excluded=('rhef','larson_sekanina')
    disabled=[];changed=False
    if basic:
        changes=[(getattr(window,'sec_'+name).chk_active,False,name.upper()) for name in excluded]
        changes += [(window.chk_achf_adaptive,False,'ACHF Adaptive'),
                    (window.achf_ael_controls['ael_iso_01']['enabled'],False,'ACHF ISO 01')]
        # A disabled legacy ACHF parent means its stored include flags were inactive.
        if not window.sec_achf.is_filter_active():
            changes += [(controls['enabled'],False,'') for controls in window.achf_ael_controls.values()]
        for widget,value,name in changes:
            if widget.isChecked()!=value:
                with QSignalBlocker(widget):widget.setChecked(value)
                changed=True
                if name:disabled.append(name)
        for selector,index in [(window.combo_wow_bilateral,2),(window.combo_nrgf_statistics,0),
                               (window.combo_achf_variant,2)]:
            if selector.currentIndex()!=index:
                with QSignalBlocker(selector):selector.setCurrentIndex(index)
                changed=True
        sync_achf_master(window)
        for widget in widgets.values():
            if isinstance(widget,QSlider):set_control_visible(widget,bool(widget.property('mix_only')) or bool(widget.property('bounded_contrast_control')) or widget is window.sl_wow_noise_reduction)
            elif widget not in (window.combo_achf_variant,window.combo_nafe_method) and not widget.property('bounded_contrast_control') and not hasattr(widget,'isChecked'):
                widget.hide()
    for name in excluded:getattr(window,'sec_'+name).setVisible(not basic)
    for variant,card in window.achf_cards.items():
        card.setVisible(not basic or variant in ('ael_iso_04','ael_angular_4'))
    window.sec_achf.hide();window.combo_achf_variant.hide()
    window.sec_wow.title_text='WOW · AEL edge-aware' if basic else 'WOW'
    window.sec_wow._update_header_text()
    window.update_wow_controls(preserve_settings=True)
    window._update_prominence_mode()
    text=('Basic: disabled '+', '.join(disabled)+'. Numeric settings retained.' if disabled else
          'Basic uses AEL variants; excluded filters are off.' if basic else '')
    window.ui_level_note.setText(text);window.ui_level_note.setVisible(bool(text))
    if changed and recalculate and not getattr(window,'_restoring_settings',False):
        window.dispatch_pipeline_request_if_auto()
