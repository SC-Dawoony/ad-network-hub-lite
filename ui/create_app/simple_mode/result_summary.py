"""Result Summary Section"""
import streamlit as st
import pandas as pd


def render_result_summary():
    """Render creation results summary section"""
    if not st.session_state.get("creation_results"):
        return
    
    st.divider()
    st.markdown("### 📊 생성 결과 요약")
    
    # Create a modal/popup style summary with expander
    with st.expander("📋 전체 생성 결과 보기", expanded=True):
        results = st.session_state.creation_results
        
        if results:
            # Create summary table
            summary_data = []
            
            for network_key, network_data in results.items():
                network_name = network_data.get("network", network_key)
                apps = network_data.get("apps", [])
                units = network_data.get("units", [])
                
                # Add app results
                for app in apps:
                    summary_data.append({
                        "네트워크": network_name,
                        "OS (Platform)": app.get("platform", "N/A"),
                        "App": app.get("app_name", "N/A"),
                        "Ad Unit": "-",
                        "Unit Type": "-",
                        "성공 여부": "✅ 성공" if app.get("success") else "❌ 실패"
                    })
                
                # Add unit results
                for unit in units:
                    success_status = "✅ 성공" if unit.get("success") else f"❌ 실패: {unit.get('error', 'Unknown')}"
                    summary_data.append({
                        "네트워크": network_name,
                        "OS (Platform)": unit.get("platform", "N/A"),
                        "App": unit.get("app_name", "N/A"),
                        "Ad Unit": unit.get("unit_name", "N/A"),
                        "Unit Type": unit.get("unit_type", "N/A"),
                        "성공 여부": success_status
                    })
            
            if summary_data:
                df = pd.DataFrame(summary_data)
                
                # Style the dataframe
                styled_df = df.style.applymap(
                    lambda x: "background-color: #d4edda; color: #155724" if "✅" in str(x) else "background-color: #f8d7da; color: #721c24" if "❌" in str(x) else "",
                    subset=["성공 여부"]
                )
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Summary statistics
                total_apps = sum(len(r.get("apps", [])) for r in results.values())
                total_units = sum(len(r.get("units", [])) for r in results.values())
                successful_apps = sum(sum(1 for app in r.get("apps", []) if app.get("success")) for r in results.values())
                successful_units = sum(sum(1 for unit in r.get("units", []) if unit.get("success")) for r in results.values())
                
                st.markdown("#### 📈 통계")
                stat_cols = st.columns(4)
                with stat_cols[0]:
                    st.metric("총 App 생성", total_apps, f"성공: {successful_apps}")
                with stat_cols[1]:
                    st.metric("총 Unit 생성", total_units, f"성공: {successful_units}")
                with stat_cols[2]:
                    app_success_rate = (successful_apps / total_apps * 100) if total_apps > 0 else 0
                    st.metric("App 성공률", f"{app_success_rate:.1f}%")
                with stat_cols[3]:
                    unit_success_rate = (successful_units / total_units * 100) if total_units > 0 else 0
                    st.metric("Unit 성공률", f"{unit_success_rate:.1f}%")
            else:
                st.info("생성된 항목이 없습니다.")
        else:
            st.info("생성 결과가 없습니다.")

