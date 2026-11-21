using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.Events;

namespace MergeBeast
{
    public class ScreenManager : MonoBehaviour
    {
        private static ScreenManager _instance;
        public static ScreenManager Instance => _instance;

        [Header("Confirm")]
        [SerializeField] private GameObject _pnConfirm;
        [SerializeField] private GameObject _pnCongrat;
        [SerializeField] private GameObject _objPopup;
        [SerializeField] private Text _txtConfirm;
        [SerializeField] private Text _txtCongrat;
        [SerializeField] private UIButton _btnOK;
        [SerializeField] private UIButton _btnOKCongrat;
        [SerializeField] private UIButton _btnCancel;
        [SerializeField] private Toggle _tgAskAgain;


        private Dictionary<EnumDefine.SCREEN, GameObject> _dictionScreen;
        private UnityAction _actionOK;
        private UnityAction _actionCancel;
        private Stack<GameObject> _stackScr;

        private Dictionary<int, int> _dictionCheck;
        private int _idConfirm;

        // Use this for initialization
        void Start()
        {
            if (_instance == null) _instance = this;
            _dictionScreen = new Dictionary<EnumDefine.SCREEN, GameObject>();
            _dictionCheck = new Dictionary<int, int>();
            _stackScr = new Stack<GameObject>();

            foreach(Transform child in this.transform)
            {
                BaseScreen scr = child.GetComponent<BaseScreen>();
                if (scr != null)
                    _dictionScreen.Add(scr.Screen, child.gameObject);
            }

            _btnOK?.onClick.AddListener(this.OnClickOK);
            _btnOKCongrat?.onClick.AddListener(this.OnClickOK);
            _btnCancel?.onClick.AddListener(this.OnClickCancle);
            _tgAskAgain?.onValueChanged.AddListener((bool s) => OnChangeCheck(s));
        }

        private void OnChangeCheck(bool isOn)
        {
            if (isOn)
            {
                if (!_dictionCheck.ContainsKey(_idConfirm)) _dictionCheck.Add(_idConfirm, 1);
            }
            else
            {
                if (_dictionCheck.ContainsKey(_idConfirm)) _dictionCheck.Remove(_idConfirm);
            }
        }

        /// <summary>
        /// 打开界面。
        ///
        /// showInter：插屏的唯一入口。
        ///   · true  —— 只有玩家主动点「菜单栏」按钮（升级 / 道具 / 图鉴 / 商店 / 升星商店 /
        ///              灵魂商店 / 进阶 / 设置）时才传，打开面板的同时投一次插屏；
        ///   · false —— 默认值。领奖励弹窗、新兽解锁、教程、宝石不足转充值等内部跳转一律不弹。
        ///
        /// 是否真的能弹出来仍然由抖音 SDK 判定（启动 15 秒内、两次间隔 30 秒内都会跳过），
        /// 这里不写任何秒表。
        /// </summary>
        public void ActiveScreen(EnumDefine.SCREEN scr, bool showInter = false)
        {
            if (_dictionScreen.ContainsKey(scr))
            {
                _dictionScreen[scr].SetActive(true);
                _stackScr.Push(_dictionScreen[scr]);

                if (showInter)
                    AdsManager.Instance?.OnShowInter();
            }
        }

        public void DeActiveScreen()
        {
            if (_stackScr.Count <= 0) return;

            GameObject obj = _stackScr.Pop();
            obj.SetActive(false);
            if(_stackScr.Count > 0)
            {
                GameObject pek = _stackScr.Peek();
                pek.SetActive(true);
            }

            // 关闭面板（点「获取」领完奖励、返回、下一关…）不再触发插屏。
            // 插屏只在 ActiveScreen(菜单按钮) 里投，避免玩家每次领东西都被广告打断。
        }

        public void ShowConfirm(int id, string mgs,UnityAction action = null,UnityAction cancle = null)
        {
            _idConfirm = id;

            if (_dictionCheck.ContainsKey(id))
            {
                if(_dictionCheck[id] == 1)
                {
                    if (id != 1)
                        action?.Invoke();
                }
            }
            else
            {
                _objPopup.SetActive(true);
                _txtConfirm.text = mgs;
                _actionOK = action;
                _actionCancel = cancle;
                _pnConfirm.SetActive(true);
                _pnCongrat.SetActive(false);
                _tgAskAgain.isOn = false;
            }
        }

        public void ShowCfGem(string mgs, UnityAction action = null)
        {
            _objPopup.SetActive(true);
            _txtConfirm.text = mgs;
            _actionOK = action;
            _pnConfirm.SetActive(true);
            _pnCongrat.SetActive(false);
        }

        public void ShowNoti(string mgs)
        {
            _pnConfirm.SetActive(false);
            _pnCongrat.SetActive(true);
            _txtCongrat.text = mgs;
            _objPopup.SetActive(true);
            _actionOK = null;
        }

        private void OnClickOK()
        {
            _objPopup.SetActive(false);
            _actionOK?.Invoke();
        }

        private void OnClickCancle()
        {
            _actionCancel?.Invoke();
            _actionCancel = null;
        }
    }
}
