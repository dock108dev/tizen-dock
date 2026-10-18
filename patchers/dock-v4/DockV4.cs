using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Security.Cryptography;
using System.Text.Json;
if(args.Length<4||args.Length>5)throw new ArgumentException("input output reference-directory asset-directory [artwork-map.json]");
if(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant()!="72a8ed55110fdf5476b6662426a9f65a41b9e925e7e6337afe7c5a90053617e5")throw new Exception("Unqualified renderer input");
var resolver=new DefaultAssemblyResolver();resolver.AddSearchDirectory(args[2]);resolver.AddSearchDirectory(System.Runtime.InteropServices.RuntimeEnvironment.GetRuntimeDirectory());
using var a=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters{AssemblyResolver=resolver});
using var flux=AssemblyDefinition.ReadAssembly(Path.Combine(args[2],"Tizen.TV.FLUX.Component.dll"));
using var nui=AssemblyDefinition.ReadAssembly(Path.Combine(args[2],"Tizen.NUI.dll"));
var mod=a.MainModule;var tile=mod.Types.Single(t=>t.Name=="TileView");var content=mod.Types.Single(t=>t.Name=="ContentItemView");
MethodReference F(string type,string name,int count=-1)=>mod.ImportReference(flux.MainModule.Types.Single(t=>t.Name==type).Methods.Single(m=>m.Name==name&&(count<0||m.Parameters.Count==count)));
MethodReference N(string type,string name,int count=-1)=>mod.ImportReference(nui.MainModule.Types.Single(t=>t.FullName==type).Methods.Single(m=>m.Name==name&&(count<0||m.Parameters.Count==count)));
// App shortcuts get private backplates; other Samsung controls retain shared styling.
var original=tile.Methods.Single(m=>m.IsConstructor);
var ctor=new MethodDefinition(".ctor",original.Attributes,mod.TypeSystem.Void);
ctor.Parameters.Add(new ParameterDefinition("preset",ParameterAttributes.None,mod.TypeSystem.String));
ctor.Parameters.Add(new ParameterDefinition("shareBackplate",ParameterAttributes.None,mod.TypeSystem.Boolean));tile.Methods.Add(ctor);
var il=ctor.Body.GetILProcessor();
foreach(var i in original.Body.Instructions){
 if(i.Operand is MethodReference m&&m.DeclaringType.Name=="Card"&&m.Name==".ctor"){
  il.Append(Instruction.Create(OpCodes.Ldarg_2));il.Append(Instruction.Create(OpCodes.Call,F("Card",".ctor",2)));
 }else{var copy=Instruction.Create(OpCodes.Nop);copy.OpCode=i.OpCode;copy.Operand=i.Operand;il.Append(copy);}
}
var cc=content.Methods.Single(m=>m.IsConstructor);var ci=cc.Body.GetILProcessor();
var baseCall=cc.Body.Instructions.Single(i=>i.Operand is MethodReference m&&m.DeclaringType.Name=="TileView"&&m.Name==".ctor");
ci.InsertBefore(baseCall,Instruction.Create(OpCodes.Ldc_I4_0));baseCall.Operand=ctor;
foreach(var i in cc.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_R4)){
 if(Math.Abs((float)i.Operand-1.18f)<.001)i.Operand=1.08f;
 else if(Math.Abs((float)i.Operand-1.08f)<.001)i.Operand=1.04f;
}
var view=nui.MainModule.Types.Single(t=>t.FullName=="Tizen.NUI.BaseComponents.View");
var ring=new FieldDefinition("dockFocusRing",FieldAttributes.Private,mod.ImportReference(flux.MainModule.Types.Single(t=>t.Name=="ImageBox")));content.Fields.Add(ring);
var helper=new MethodDefinition("StyleDockFocus",MethodAttributes.Private|MethodAttributes.HideBySig,mod.TypeSystem.Void);
helper.Parameters.Add(new ParameterDefinition("focused",ParameterAttributes.None,mod.TypeSystem.Boolean));content.Methods.Add(helper);
var h=helper.Body.GetILProcessor();
void E(Instruction i)=>h.Append(i);
var hide=N(view.FullName,"Hide",0);var show=N(view.FullName,"Show",0);var clear=N(view.FullName,"ClearBackground",0);
var get=F("Component","GetElement",1);
// Hide this app's private rectangular UIPlate, including all of its shadows.
E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldstr,"Background"));E(Instruction.Create(OpCodes.Callvirt,get));E(Instruction.Create(OpCodes.Dup));
var found=Instruction.Create(OpCodes.Callvirt,hide);E(Instruction.Create(OpCodes.Brtrue_S,found));E(Instruction.Create(OpCodes.Pop));var next=Instruction.Create(OpCodes.Ldarg_0);E(Instruction.Create(OpCodes.Br_S,next));E(found);E(next);E(Instruction.Create(OpCodes.Callvirt,clear));
E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));var haveRing=Instruction.Create(OpCodes.Nop);E(Instruction.Create(OpCodes.Brtrue_S,haveRing));
E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldstr,args[3].TrimEnd('/')+"/focus-ring-v4.png"));E(Instruction.Create(OpCodes.Newobj,F("ImageBox",".ctor",1)));E(Instruction.Create(OpCodes.Stfld,ring));
foreach(var prop in new[]{"WidthResizePolicy","HeightResizePolicy"}){E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Ldc_I4_2));E(Instruction.Create(OpCodes.Callvirt,N(view.FullName,"set_"+prop,1)));}
E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Ldc_I4_0));E(Instruction.Create(OpCodes.Callvirt,N(view.FullName,"set_Focusable",1)));
E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Callvirt,N(view.FullName,"Add",1)));
E(haveRing);E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Callvirt,N(view.FullName,"RaiseToTop",0)));
E(Instruction.Create(OpCodes.Ldarg_1));var no=Instruction.Create(OpCodes.Ldarg_0);E(Instruction.Create(OpCodes.Brfalse_S,no));E(Instruction.Create(OpCodes.Ldarg_0));E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Callvirt,show));E(Instruction.Create(OpCodes.Ret));E(no);E(Instruction.Create(OpCodes.Ldfld,ring));E(Instruction.Create(OpCodes.Callvirt,hide));E(Instruction.Create(OpCodes.Ret));
foreach(var name in new[]{"BindData","OnFocused","OnUnfocused"}){
 var m=content.Methods.Single(m=>m.Name==name);var ip=m.Body.GetILProcessor();var ret=m.Body.Instructions.Last();
 ip.InsertBefore(ret,Instruction.Create(OpCodes.Ldarg_0));
 if(name=="BindData"){ip.InsertBefore(ret,Instruction.Create(OpCodes.Ldarg_0));ip.InsertBefore(ret,Instruction.Create(OpCodes.Call,tile.Methods.Single(m=>m.Name=="get_Focused")));}
 else ip.InsertBefore(ret,Instruction.Create(name=="OnFocused"?OpCodes.Ldc_I4_1:OpCodes.Ldc_I4_0));
 ip.InsertBefore(ret,Instruction.Create(OpCodes.Call,helper));
}
// Optional owner-local artwork map; bundled brand artwork is never published.
if(args.Length==5){
// Match the mask's pixel dimensions to the 512px artwork. DALi's default
// mask sizing crops a larger source to a smaller mask before display scaling.
foreach(var i in content.Methods.Single(m=>m.Name=="BindData").Body.Instructions)
 if(i.OpCode==OpCodes.Ldstr&&i.Operand is string path&&path.EndsWith("compact-dock-icon-mask-v2.png"))i.Operand=args[3].TrimEnd('/')+"/compact-dock-icon-mask-v4.png";
 var map=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(args[4]))!;
 var choose=new MethodDefinition("ChooseDockIcon",MethodAttributes.Private|MethodAttributes.Static|MethodAttributes.HideBySig,mod.TypeSystem.String);
 choose.Parameters.Add(new ParameterDefinition("title",ParameterAttributes.None,mod.TypeSystem.String));choose.Parameters.Add(new ParameterDefinition("fallback",ParameterAttributes.None,mod.TypeSystem.String));content.Methods.Add(choose);
 var eq=new MethodReference("op_Equality",mod.TypeSystem.Boolean,mod.TypeSystem.String){HasThis=false};eq.Parameters.Add(new ParameterDefinition(mod.TypeSystem.String));eq.Parameters.Add(new ParameterDefinition(mod.TypeSystem.String));
 var cp=choose.Body.GetILProcessor();
 foreach(var pair in map){var skip=Instruction.Create(OpCodes.Nop);cp.Append(Instruction.Create(OpCodes.Ldarg_0));cp.Append(Instruction.Create(OpCodes.Ldstr,pair.Key));cp.Append(Instruction.Create(OpCodes.Call,eq));cp.Append(Instruction.Create(OpCodes.Brfalse_S,skip));cp.Append(Instruction.Create(OpCodes.Ldstr,args[3].TrimEnd('/')+"/"+Path.GetFileName(pair.Value)));cp.Append(Instruction.Create(OpCodes.Ret));cp.Append(skip);}
 cp.Append(Instruction.Create(OpCodes.Ldarg_1));cp.Append(Instruction.Create(OpCodes.Ret));
 var bind=content.Methods.Single(m=>m.Name=="BindData");var bp=bind.Body.GetILProcessor();
 var current=(MethodReference)bind.Body.Instructions.First(i=>i.Operand is MethodReference m&&m.Name=="get_CurrentElement").Operand;
 var title=(MethodReference)bind.Body.Instructions.First(i=>i.Operand is MethodReference m&&m.Name=="get_Title").Operand;
 var anchor=bind.Body.Instructions.First(i=>i.OpCode==OpCodes.Stfld&&i.Operand is FieldReference f&&f.Name=="unfocusedIconURL").Next;
 foreach(var field in content.Fields.Where(f=>f.Name=="focusedIconURL"||f.Name=="unfocusedIconURL")){
  foreach(var i in new[]{Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldarg_1),Instruction.Create(OpCodes.Callvirt,current),Instruction.Create(OpCodes.Callvirt,title),Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,field),Instruction.Create(OpCodes.Call,choose),Instruction.Create(OpCodes.Stfld,field)})bp.InsertBefore(anchor,i);
 }
}
a.Write(args[1]);
using var check=AssemblyDefinition.ReadAssembly(args[1]);
if(check.MainModule.AssemblyReferences.Any(r=>r.Name=="System.Private.CoreLib"))throw new Exception("Host runtime reference");
File.WriteAllText(args[1]+".json",JsonSerializer.Serialize(new{sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))).ToLowerInvariant(),baseline="qualified-v3",focusedScale=1.08,privateAppBackplate=true,roundedFocusRing=true,deviceValidation="pending"},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine("Built isolated app backplate, rounded focus ring and reduced focus zoom. Check the result on the target TV.");
