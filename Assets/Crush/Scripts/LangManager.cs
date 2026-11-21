using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class LangManager : MonoBehaviour
{
    private static LangManager instance;
    public static LangManager Instance
    {
        get
        {
            if (instance == null)
            {
                GameObject gameObject = new GameObject("LangManager");
                instance = gameObject.AddComponent<LangManager>();
                DontDestroyOnLoad(gameObject);
            }
            return instance;
        }
        private set { }
    }

    public static string Language = "en";
    public const string English = "en";
    public const string VietNamese = "vn";

    private Dictionary<string, string> keyValuePairs = new Dictionary<string, string>();

    void Awake()
    {
        if (instance != null && instance.GetInstanceID() != this.GetInstanceID())
        {
            Destroy(gameObject);
        }
        else
        {
            instance = this as LangManager;
            DontDestroyOnLoad(gameObject);
        }

        switch (LangManager.Language)
        {
            case LangManager.English:
                keyValuePairs["LostMonster"] = "丢失 {0} 只怪物";
                keyValuePairs["Retreat"] = "撤退";
                keyValuePairs["ContentRetreat"] = "确定要离开战斗吗？";
                keyValuePairs["Damage"] = "伤害";
                keyValuePairs["DamageTaken"] = "承受伤害";
                keyValuePairs["DamagePerMonster"] = "每只怪物的伤害";
                keyValuePairs["Reward"] = "奖励";
                keyValuePairs["Okay"] = "好的";
                keyValuePairs["Stats"] = "统计";

                keyValuePairs["Atk"] = "攻击";
                keyValuePairs["Hp"] = "生命";
                keyValuePairs["Def"] = "防御";
                keyValuePairs["CritRate"] = "暴击率";
                keyValuePairs["CriteDamage"] = "暴击伤害";
                keyValuePairs["AtkPerSec"] = "每秒攻击";
                keyValuePairs["AtkRange"] = "攻击范围";
                keyValuePairs["MoveSpeed"] = "移动速度";
                keyValuePairs["EffectResistance"] = "效果抗性";
                keyValuePairs["FrenzyChance"] = "狂暴几率";
                keyValuePairs["DodgeRate"] = "闪避率";
                keyValuePairs["StunChance"] = "眩晕几率";
                keyValuePairs["StunTime"] = "眩晕时间";
                keyValuePairs["AoERadius"] = "范围半径";
                keyValuePairs["AoEDmg"] = "范围伤害";
                keyValuePairs["UltimateAtk"] = "终极攻击";
                keyValuePairs["KnightShieldHP"] = "骑士护盾";
                keyValuePairs["BonusLoot"] = "额外掉落";
                keyValuePairs["FreezeChance"] = "冰冻几率";
                keyValuePairs["FreezeTime"] = "冰冻时间";
                keyValuePairs["FreezeExplotionDmg"] = "冰爆伤害";
                keyValuePairs["BurnChance"] = "燃烧几率";
                keyValuePairs["BurnTime"] = "燃烧时间";
                keyValuePairs["BurnDmg"] = "燃烧伤害";
                keyValuePairs["PoisonChance"] = "中毒几率";
                keyValuePairs["PoisonDmg"] = "中毒伤害";

                keyValuePairs["Passive"] = "被动";
                keyValuePairs["Active"] = "主动";
                keyValuePairs["NoteSkillOn"] = "下次 <sprite=0> 进化：<color=#FC7374>{0}</color>";
                keyValuePairs["NoteSkillOff"] = "该技能将在怪物达到 {0} <sprite=0> 时解锁";

                keyValuePairs["time"] = "次";
                keyValuePairs["times"] = "次";
                keyValuePairs["OutOfPlayAmount"] = "<sprite=10> 不足";
                keyValuePairs["OutOfPlayAmountDes"] = "用 {1} <sprite=6> 购买 {0} <sprite=10>？\n今日已购买 {2} {3}";
                break;
            case LangManager.VietNamese:
                break;
        }

    }

    public string Get(string key)
    {
        if (keyValuePairs.ContainsKey(key)) return keyValuePairs[key];
        return key;
    }
}
