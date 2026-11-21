using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MergeBeast;
using UnityEngine.UI;
using System;
using Observer;
namespace Tiledom
{
    public class BuyTurnController : MonoBehaviour
    {
        [SerializeField] Button btnOk;
        [SerializeField] Text txtNote;

        int countBuy;

        private void OnEnable() {
            countBuy = PlayerPrefs.GetInt(StringDefine.COUNT_BUY_TURN, 0);
            DateTime lastDay = DateTime.Parse(PlayerPrefs.GetString(StringDefine.LAST_DAY_BUY_TURN, DateTime.Today.AddDays(-1).ToString()));
            DateTime today = DateTime.Today;
            int dayDiff = (today - lastDay).Days;
            if(dayDiff > 0) {
                countBuy = 0;
            }

            txtNote.text = $"花费 {Utils.FormatNumber((countBuy + 1 ) * 25)} 宝石购买 {Config.TILE_TURN_PER_DAY} 次步数";
            txtNote.text += $"\n今日已购买 {countBuy} 次";

        }
        void Start() {
            btnOk.onClick.AddListener(() => Buy());      
        }

        void Buy() {
            countBuy++;
            int money = countBuy * 25;
            if(Utils.GetCurrentRubyMoney() >= money) {
                Utils.AddRubyCoin(-money);
                this.PostEvent(EventID.OnUpDateMoney);
                PlayerPrefs.SetInt(StringDefine.COUNT_TILE_TURN, 5);
                

                PlayerPrefs.SetInt(StringDefine.COUNT_BUY_TURN, countBuy);
                PlayerPrefs.SetString(StringDefine.LAST_DAY_BUY_TURN, DateTime.Today.ToString());
                
                this.PostEvent(EventID.OnUpdateTileTurn);

                gameObject.SetActive(false);
            } else {
                LevelController.instance.ShowToast("钻石不足");
            }
        }
    }
}