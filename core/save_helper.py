# -*- coding: utf-8 -*-
"""Save Helper — unified save form"""
import time as _time
import streamlit as st


def save_button(form_key, save_fn, label="💾 حفظ", cooldown=3.0,
                use_container_width=True, type="primary"):
    last_key = "_cooldown_" + form_key
    result_key = "_result_" + form_key

    last_save = st.session_state.get(last_key, 0)
    now = _time.time()
    elapsed = now - last_save
    too_soon = elapsed < cooldown

    def _wrapper():
        st.session_state[last_key] = _time.time()
        try:
            save_fn()
            try:
                st.cache_data.clear()
            except Exception:
                pass
        except Exception as e:
            st.session_state[result_key] = "err:" + str(e)[:200]

    btn_label = label
    if too_soon:
        remaining = int(cooldown - elapsed) + 1
        btn_label = "{} (انتظر {}ث)".format(label, remaining)

    st.button(
        btn_label,
        type=type,
        use_container_width=use_container_width,
        key=form_key + "_btn",
        on_click=_wrapper,
        disabled=too_soon,
    )

    result = st.session_state.get(result_key)
    if result == "ok":
        st.success("✅ تم الحفظ")
        st.session_state.pop(result_key, None)
    elif result and str(result).startswith("err:"):
        st.error("❌ " + str(result)[4:])
        st.session_state.pop(result_key, None)


def mark_result(form_key, success=True, error=None):
    result_key = "_result_" + form_key
    if success:
        st.session_state[result_key] = "ok"
    else:
        st.session_state[result_key] = "err:" + str(error)[:200]
